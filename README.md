# MPlib: a Lightweight Motion Planning Library

<p align="center">
  <img src="https://raw.githubusercontent.com/haosulab/MPlib/main/docs/demo.gif">
</p>

[![PyPI - Version](https://img.shields.io/pypi/v/mplib)](https://pypi.org/project/mplib/)
[![Downloads](https://static.pepy.tech/badge/mplib)](https://pepy.tech/project/mplib)
[![Build python wheels](https://img.shields.io/github/actions/workflow/status/haosulab/MPlib/build_and_publish.yml)](https://github.com/haosulab/MPlib/releases/tag/nightly)
[![Documentation](https://img.shields.io/readthedocs/motion-planning-lib)](https://motion-planning-lib.readthedocs.io/)
[![License](https://img.shields.io/github/license/haosulab/MPlib)](https://github.com/haosulab/MPlib?tab=MIT-1-ov-file#readme)

MPlib is a lightweight python package for motion planning,
which is decoupled from ROS and is easy to set up.  
With a few lines of python code, one can achieve most of the motion planning
functionalities in robot manipulation.

## Installation

This fork is for providing the SD (desired duration) variant of TOPPRA.
I did not have the time to fix the new build system, so installation is hacked as follows:

```
git clone --recursive https://github.com/vonHartz/MPlib.git
pip install mplib
cp MPlib/mplib/planner.py ~/miniconda3/envs/<NAME OF YOUR CONDA ENV>/lib/python3.10/site-packages/mplib/planner.py
```

## Old installation instructions

(This process currently fails. Fix it. Might pull inspiration from the official MPLIB github-flow compilation.)

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

See our [tutorial](https://motion-planning-lib.readthedocs.io/latest/tutorials/getting_started.html) for detailed usage and examples.
