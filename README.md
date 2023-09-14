# MPlib
MPlib is a lightweight python package for motion planning, which is decoupled from ROS and is easy to set up. With a few lines of python code, one can achieve most of the motion planning functionalities in robot manipulation.

<p align="center">
  <img src="demo.gif">
</p>

## Installation

This fork is for easily building MPlib from source to support Python versions outside what the original package offers, eg. Python 3.10.


Clone the repo, then try either of the following:

### Docker
You can try to build the wheel for MPlib in the manylinux container and then install it on your local machine.
```
RUN git clone --single-branch -b v1.9.7 --depth 1 https://github.com/OctoMap/octomap.git && \
    cd octomap/octomap && mkdir build && cd build && \
    cmake .. && make -j && make install && \
    rm -rf /workspace/octomap

# v0.6.1 does not work, use newer instead
RUN git clone --single-branch https://github.com/flexible-collision-library/fcl.git && \
    cd fcl && git checkout 7fcdc7f09bedb3d9544bfce067b01298873ad906 && mkdir build && cd build && \
    cmake .. && make -j && make install && \
    rm -rf /workspace/fcl

cd MPlib/docker
docker build -t mplib .
docker run --rm -v $(pwd):/workspace mplib /bin/bash -c "cd /workspace && python3.10 setup.py bdist_wheel"
pip install -r requirements.txt
pip install dist/mplib-0.0.8-cp310-cp310-linux_x86_64.whl
```

### Manual installation
You can also try to do it manually, though there I run into an error when trying to build the wheel.
Install all the libs listed in the Dockerfile on your local machine. You can just copy the lines from the Dockerfile - though you might need to run `sudo make install`, depending on your local cmake config.

## Usage

See our [tutorial](https://sapien.ucsd.edu/docs/latest/tutorial/motion_planning/getting_started.html) for detailed usage and examples.
