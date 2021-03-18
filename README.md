# URDF2CasADi
A module for generating the forward kinematics of a robot from a URDF. It can generate the forward kinematics represented as a dual quaternion or a transformation matrix. `urdf2casadi` works both in python 2 and 3, and any platform that supports `CasADi` and `urdf_parser_py`.

*DISCLAIMER*: as that's a forked repo from the urdf2casadi original one, be sure to cite the original authors if you use this! You will find everything you need at the bottom.

## Installation
1. [Get CasADi](https://github.com/casadi/casadi/wiki/InstallationInstructions) (e.g. `pip install casadi`).
2.  Run `pip install --user .` in the folder (`--user` specifies that it is a local install).


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

