from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
from sapien import Entity, Scene
from sapien.physx import (
    PhysxArticulation,
    PhysxArticulationLinkComponent,
    PhysxCollisionShapeBox,
    PhysxCollisionShapeCapsule,
    PhysxCollisionShapeConvexMesh,
    PhysxCollisionShapeCylinder,
    PhysxCollisionShapePlane,
    PhysxCollisionShapeSphere,
    PhysxCollisionShapeTriangleMesh,
    PhysxRigidBaseComponent,
)
from transforms3d.euler import euler2quat

from ..planner import Planner
from ..pymp import ArticulatedModel, PlanningWorld, Pose
from ..pymp.collision_detection.fcl import (
    Box,
    BVHModel,
    Capsule,
    CollisionObject,
    Convex,
    Cylinder,
    FCLObject,
    Halfspace,
    Sphere,
    collide,
    distance,
)
from ..pymp.planning import ompl
from .srdf_exporter import export_srdf
from .urdf_exporter import export_kinematic_chain_urdf


class SapienPlanningWorld(PlanningWorld):
    def __init__(
        self,
        sim_scene: Scene,
        planned_articulations: list[PhysxArticulation] = [],  # noqa: B006
    ):
        """
        Creates an mplib.pymp.planning_world.PlanningWorld from a sapien.Scene.

        :param planned_articulations: list of planned articulations.
        """
        super().__init__([], [])
        self._sim_scene = sim_scene

        articulations: list[PhysxArticulation] = sim_scene.get_all_articulations()
        actors: list[Entity] = sim_scene.get_all_actors()

        for articulation in articulations:
            urdf_str = export_kinematic_chain_urdf(articulation)
            srdf_str = export_srdf(articulation)

            # Convert all links to FCLObject
            collision_links = [
                (link.name, fcl_obj)
                for link in articulation.links
                if (fcl_obj := self.convert_physx_component(link)) is not None
            ]

            articulated_model = ArticulatedModel.create_from_urdf_string(
                urdf_str,
                srdf_str,
                collision_links=collision_links,
                gravity=sim_scene.get_physx_system().config.gravity,  # type: ignore
                link_names=[link.name for link in articulation.links],
                joint_names=[j.name for j in articulation.active_joints],
                verbose=False,
            )
            articulated_model.set_qpos(articulation.qpos)  # update qpos  # type: ignore

            self.add_articulation(self.get_object_name(articulation), articulated_model)

        for articulation in planned_articulations:
            self.set_articulation_planned(self.get_object_name(articulation), True)

        for entity in actors:
            component = entity.find_component_by_type(PhysxRigidBaseComponent)
            assert component is not None, (
                f"No PhysxRigidBaseComponent found in {entity.name}: "
                f"{entity.components=}"
            )

            # Convert collision shapes at current global pose
            self.add_normal_object(
                self.get_object_name(entity),
                self.convert_physx_component(component),  # type: ignore
            )

    def update_from_simulation(self, *, update_attached_object: bool = True) -> None:
        """
        Updates PlanningWorld's articulations/objects pose with current Scene state.
        Note that shape's local_pose is not updated.
        If those are changed, please recreate a new SapienPlanningWorld instance.

        :param update_attached_object: whether to update the attached pose of
            all attached objects
        """
        for articulation in self._sim_scene.get_all_articulations():
            if art := self.get_articulation(self.get_object_name(articulation)):
                # set_qpos to update poses
                art.set_qpos(articulation.qpos)  # type: ignore
            else:
                raise RuntimeError(
                    f"Articulation {articulation.name} not found in PlanningWorld! "
                    "The scene might have changed since last update."
                )

        for entity in self._sim_scene.get_all_actors():
            object_name = self.get_object_name(entity)

            # If entity is an attached object
            if attached_body := self.get_attached_object(object_name):
                if update_attached_object:  # update attached pose
                    attached_body.pose = (
                        attached_body.get_attached_link_global_pose().inv()
                        * entity.pose  # type: ignore
                    )
                attached_body.update_pose()
            elif fcl_obj := self.get_normal_object(object_name):
                # Overwrite the object
                self.add_normal_object(
                    object_name,
                    FCLObject(
                        object_name,
                        entity.pose,  # type: ignore
                        fcl_obj.shapes,
                        fcl_obj.shape_poses,
                    ),
                )
            else:
                raise RuntimeError(
                    f"Entity {entity.name} not found in PlanningWorld! "
                    "The scene might have changed since last update."
                )

    @staticmethod
    def get_object_name(obj: PhysxArticulation | Entity) -> str:
        """
        Constructs a unique name for the corresponding mplib object.
        This is necessary because mplib objects assume unique names.

        :param obj: a SAPIEN object
        :return: the unique mplib object name
        """
        if isinstance(obj, PhysxArticulation):
            return f"{obj.name}_{obj.root.entity.per_scene_id}"
        elif isinstance(obj, Entity):
            return f"{obj.name}_{obj.per_scene_id}"
        else:
            raise NotImplementedError(f"Unknown SAPIEN object type {type(obj)}")

    @staticmethod
    def convert_physx_component(comp: PhysxRigidBaseComponent) -> FCLObject | None:
        """
        Converts a SAPIEN physx.PhysxRigidBaseComponent to an FCLObject.
        All shapes in the returned FCLObject are already set at their world poses.

        :param comp: a SAPIEN physx.PhysxRigidBaseComponent.
        :return: an FCLObject containing all collision shapes in the Physx component.
            If the component has no collision shapes, return ``None``.
        """
        shapes: list[CollisionObject] = []
        shape_poses: list[Pose] = []
        for shape in comp.collision_shapes:
            shape_poses.append(shape.local_pose)  # type: ignore

            if isinstance(shape, PhysxCollisionShapeBox):
                c_geom = Box(side=shape.half_size * 2)
            elif isinstance(shape, PhysxCollisionShapeCapsule):
                c_geom = Capsule(radius=shape.radius, lz=shape.half_length * 2)
                # NOTE: physx Capsule has x-axis along capsule height
                # FCL Capsule has z-axis along capsule height
                shape_poses[-1] *= Pose(q=euler2quat(0, np.pi / 2, 0))
            elif isinstance(shape, PhysxCollisionShapeConvexMesh):
                assert np.allclose(
                    shape.scale, 1.0
                ), f"Not unit scale {shape.scale}, need to rescale vertices?"
                c_geom = Convex(vertices=shape.vertices, faces=shape.triangles)
            elif isinstance(shape, PhysxCollisionShapeCylinder):
                c_geom = Cylinder(radius=shape.radius, lz=shape.half_length * 2)
                # NOTE: physx Cylinder has x-axis along cylinder height
                # FCL Cylinder has z-axis along cylinder height
                shape_poses[-1] *= Pose(q=euler2quat(0, np.pi / 2, 0))
            elif isinstance(shape, PhysxCollisionShapePlane):
                raise NotImplementedError(
                    "Support for Plane collision is not implemented yet in mplib, "
                    "need fcl::Plane"
                )
            elif isinstance(shape, PhysxCollisionShapeSphere):
                c_geom = Sphere(radius=shape.radius)
            elif isinstance(shape, PhysxCollisionShapeTriangleMesh):
                c_geom = BVHModel()
                c_geom.begin_model()
                c_geom.add_sub_model(vertices=shape.vertices, faces=shape.triangles)  # type: ignore
                c_geom.end_model()
            else:
                raise TypeError(f"Unknown shape type: {type(shape)}")
            shapes.append(CollisionObject(c_geom))

        if len(shapes) == 0:
            return None

        return FCLObject(
            comp.name
            if isinstance(comp, PhysxArticulationLinkComponent)
            else SapienPlanningWorld.get_object_name(comp.entity),
            comp.entity.pose,  # type: ignore
            shapes,
            shape_poses,
        )


class SapienPlanner(Planner):
    def __init__(
        self,
        sapien_planning_world: SapienPlanningWorld,
        move_group: str,
        *,
        joint_vel_limits: Optional[Sequence[float] | np.ndarray] = None,
        joint_acc_limits: Optional[Sequence[float] | np.ndarray] = None,
    ):
        """
        Creates an mplib.planner.Planner from a SapienPlanningWorld.

        :param sapien_planning_world: a SapienPlanningWorld created from sapien.Scene
        :param move_group: name of the move group (end effector link)
        :param joint_vel_limits: joint velocity limits for time parameterization
        :param joint_acc_limits: joint acceleration limits for time parameterization
        """
        self.planning_world = sapien_planning_world
        self.acm = self.planning_world.get_allowed_collision_matrix()

        if len(planned_arts := self.planning_world.get_planned_articulations()) != 1:
            raise NotImplementedError("Must have exactly one planned articulation")
        self.robot = planned_arts[0]
        self.pinocchio_model = self.robot.get_pinocchio_model()
        self.user_link_names = self.pinocchio_model.get_link_names()
        self.user_joint_names = self.pinocchio_model.get_joint_names()

        self.joint_name_2_idx = {}
        for i, joint in enumerate(self.user_joint_names):
            self.joint_name_2_idx[joint] = i
        self.link_name_2_idx = {}
        for i, link in enumerate(self.user_link_names):
            self.link_name_2_idx[link] = i

        assert (
            move_group in self.user_link_names
        ), f"end-effector not found as one of the links in {self.user_link_names}"
        self.move_group = move_group
        self.robot.set_move_group(self.move_group)
        self.move_group_joint_indices = self.robot.get_move_group_joint_indices()

        self.joint_types = self.pinocchio_model.get_joint_types()
        self.joint_limits = np.concatenate(self.pinocchio_model.get_joint_limits())
        if joint_vel_limits is None:
            joint_vel_limits = np.ones(len(self.move_group_joint_indices))
        if joint_acc_limits is None:
            joint_acc_limits = np.ones(len(self.move_group_joint_indices))
        self.joint_vel_limits = joint_vel_limits
        self.joint_acc_limits = joint_acc_limits
        self.move_group_link_id = self.link_name_2_idx[self.move_group]

        assert (
            len(self.joint_vel_limits)
            == len(self.joint_acc_limits)
            == len(self.move_group_joint_indices)
            <= len(self.joint_limits)
        ), (
            "length of joint_vel_limits, joint_acc_limits, and move_group_joint_indices"
            " should equal and be <= number of total joints. "
            f"{len(self.joint_vel_limits)} == {len(self.joint_acc_limits)} "
            f"== {len(self.move_group_joint_indices)} <= {len(self.joint_limits)}"
        )

        # Mask for joints that have equivalent values (revolute joints with range > 2pi)
        self.equiv_joint_mask = [
            t.startswith("JointModelR") for t in self.joint_types
        ] & (self.joint_limits[:, 1] - self.joint_limits[:, 0] > 2 * np.pi)

        self.planner = ompl.OMPLPlanner(world=self.planning_world)

    def update_from_simulation(self, *, update_attached_object: bool = True) -> None:
        """
        Updates PlanningWorld's articulations/objects pose with current Scene state.
        Note that shape's local_pose is not updated.
        If those are changed, please recreate a new SapienPlanningWorld instance.

        Directly calls ``SapienPlanningWorld.update_from_simulation()``

        :param update_attached_object: whether to update the attached pose of
            all attached objects
        """
        self.planning_world.update_from_simulation(
            update_attached_object=update_attached_object
        )