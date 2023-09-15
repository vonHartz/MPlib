# MPlib
MPlib is a lightweight python package for motion planning, which is decoupled from ROS and is easy to set up. With a few lines of python code, one can achieve most of the motion planning functionalities in robot manipulation.

<p align="center">
  <img src="demo.gif">
</p>

## Installation

This fork is for easily building MPlib from source to support Python versions outside what the original package offers, eg. Python 3.10.

```
git clone --recursive https://github.com/vonHartz/MPlib.git
cd MPlib
docker build -t mplib .
docker run --rm -v $(pwd):/workspace mplib /bin/bash -c "python3.10 -m setup bdist_wheel && auditwheel repair dist/mplib-0.0.8-cp310-cp310-linux_x86_64.whl"
pip install -r requirements.txt
pip install dist/mplib-0.0.8-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```


## Usage

See our [tutorial](https://sapien.ucsd.edu/docs/latest/tutorial/motion_planning/getting_started.html) for detailed usage and examples.
