# URDF2CASADI
A module for generating the forward kinematics of a robot from a URDF. It can generate the forward kinematics represented as a dual quaternion or a transformation matrix. `urdf2casadi` works both in python 2 and 3, and any platform that supports `CasADi` and `urdf_parser_py`.

## Installation
With ROS:
1. [Get ROS](http://www.ros.org/install/) (actually anything that installs `urdfdom_py`/`urdf_parser_py` will do).
2. [Get CasADi](https://github.com/casadi/casadi/wiki/InstallationInstructions) (e.g. `pip install casadi`).
3. Run `pip install --user .` in the folder.

Without ROS:
1. Change the `urdfdom-py` to `urdf-parser-py` in `requirements.txt` (line 3) and in `setup.py` (line 20).
2. [Get CasADi](https://github.com/casadi/casadi/wiki/InstallationInstructions) (e.g. `pip install casadi`).
3.  Run `pip install --user .` in the folder (`--user` specifies that it is a local install).

## Usage example
```python
import casadi as cs
from urdf2casadi import urdfparser as u2c
urdf_path = "../urdf/ur5_mod.urdf"
root_link = "base_link"
end_link = "tool0"
robot_parser = u2c.URDFparser()
fk_dict = robot_parser.get_forward_kinematics(root_link, end_link)
print fk_dict.keys()
<<<<<<< HEAD
# should give ['q', 'upper', 'lower', 'dual_quaternion_fk', 'joint_names', 'T_fk', 'joint_list', 'quaternion_fk']
=======
# should give ['upper', 'T_fk', 'lower', 'q', 'joint_names', 'joint_list']
>>>>>>> 10c69944730516bc76702faf0c44151dac47ddfe
forward_kinematics = fk_dict["T_fk"]
print forward_kinematics([0.3, 0.3, 0.3, 0., 0.3, 0.7])
```

## Todo/Implementation status
- [x] Forward kinematics with SE(3) matrix
- [x] Forward kinematics of rotation with quaternion
- [x] Dual Quaternions as alternative to SE(3) matrices
<<<<<<< HEAD
- [ ] Dynamics from links and their inertia tags
- [x] Denavit Hartenberg?
- [ ] unit tests
- [ ] Examples
=======
- [x] Dynamics from links and their inertia tags
- [ ] Denavit Hartenberg?
- [ ] Move numerical to a test folder
- [x] Examples
>>>>>>> 10c69944730516bc76702faf0c44151dac47ddfe
