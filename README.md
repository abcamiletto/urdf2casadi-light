# URDF2CASADI
A module for generating the forward kinematics of a robot from a URDF. It can generate the forward kinematics represented as a dual quaternion or a transformation matrix. `urdf2casadi` works both in python 2 and 3, and any platform that supports `CasADi` and `urdf_parser_py`.

## Other libraries
This module is implemented in Python, and was intended to explore a CasADi approach to forward kinematics and rigid body dynamics algorithms based on URDFs. For a more real-time control applicable alternative, consider the [Pinocchio](https://github.com/stack-of-tasks/pinocchio) library.

## Installation
1. Change the `urdfdom-py` to `urdf-parser-py` in `requirements.txt` (line 3) and in `setup.py` (line 20).
2. [Get CasADi](https://github.com/casadi/casadi/wiki/InstallationInstructions) (e.g. `pip install casadi`).
3.  Run `pip install --user .` in the folder (`--user` specifies that it is a local install).


## Citation
The results were published in "Robot Dynamics with URDF & CasADi" at ICCMA 2019. [[Preprint](http://folk.ntnu.no/tomgra/papers/Johannessen_ICCMA_2019_paper_23%20.pdf)]
```
@inproceedings{urdf2casadi,
  title={Robot Dynamics with URDF \& CasADi},
  author={Johannessen, Lill Maria Gjerde and Arbo, Mathias Hauan and Gravdahl, Jan Tommy},
  booktitle={2019 7th International Conference on Control, Mechatronics and Automation (ICCMA)},
  year={2019},
  organization={IEEE}
}
```

