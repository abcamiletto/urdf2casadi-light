"""This module contains a class for turning a chain in a URDF to a
casadi function.
"""
import casadi as cs
import numpy as np
from urdf_parser_py.urdf import URDF, Pose
from geometry import transformation_matrix as T
from geometry import plucker
from geometry import quaternion
from geometry import dual_quaternion

class URDFparser(object):
	"""Class that turns a chain from URDF to casadi functions"""
	actuated_types = ["prismatic", "revolute", "continuous"]

	def __init__(self):
		self.robot_desc = None


	def from_file(self, filename):
		"""Uses an URDF file to get robot description"""
		print filename
		self.robot_desc = URDF.from_xml_file(filename)
		#self.chain_list = robot_desc.get_chain(root, tip)

	def from_server(self, key="robot_description"):
		"""Uses a parameter server to get robot description"""
		self.robot_desc = URDF.from_parameter_server(key=key)
        #self.chain_list = robot_desc.get_chain(root, tip)

	def from_string(self, urdfstring):
		"""Uses a string to get robot description"""
		self.robot_desc = URDF.from_xml_string(urdfstring)



	def get_joint_info(self, root, tip):
		"""Using an URDF to extract a proper joint_list, actuated names and upper and lower limits for joints"""
		chain = self.robot_desc.get_chain(root, tip)
		if self.robot_desc is None:
			raise ValueError('Robot description not loaded from urdf')

		joint_list = []
		upper = []
		lower = []
		actuated_names = []
		for item in chain:
			if item in self.robot_desc.joint_map:
				joint = self.robot_desc.joint_map[item]
				joint_list += [joint]
				if joint.type in self.actuated_types:
					actuated_names += [joint.name]
					if joint.type == "continuous":
						upper += [cs.inf]
						lower += [-cs.inf]
					else:
						upper += [joint.limit.upper]
						lower += [joint.limit.lower]
					if joint.axis is None:
						joint.axis = [1., 0., 0.]
					if joint.origin is None:
						joint.origin = Pose(xyz=[0., 0., 0.],
	                                        rpy=[0., 0., 0.])
					elif joint.origin.xyz is None:
						joint.origin.xyz = [0., 0., 0.]
					elif joint.origin.rpy is None:
						joint.origin.rpy = [0., 0., 0.]

		return joint_list, actuated_names, upper, lower

	def _get_joint_list(self, root, tip):
		"""Returns list of all joints, for further use in ID- and FD algorithms"""

		chain = self.robot_desc.get_chain(root, tip)
		joint_list = []
		for item in chain:
			if item in self.robot_desc.joint_map:
				joint = self.robot_desc.joint_map[item]
				joint_list += [joint]
				if joint.type in self.actuated_types:
					if joint.axis is None:
						joint.axis = [1., 0., 0.]
					if joint.origin is None:
						joint.origin = Pose(xyz=[0., 0., 0.],
	                                        rpy=[0., 0., 0.])
					elif joint.origin.xyz is None:
						joint.origin.xyz = [0., 0., 0.]
					elif joint.origin.rpy is None:
						joint.origin.rpy = [0., 0., 0.]

		return joint_list


	def get_spatial_inertias(self, root, tip):
		if self.robot_desc is None:
			raise ValueError('Robot description not loaded from urdf')

		chain = self.robot_desc.get_chain(root, tip)
		spatial_inertias = []

		for item in chain:
			#Assuming here that root is always a base link, is this a reasonable assumption?
			#Could also just use spatial_inertias[i+1] in algorithm iterations
			if item in self.robot_desc.link_map:
				link = self.robot_desc.link_map[item]
				print link.name
				if link.inertial is not None:
					I = link.inertial.inertia
					spatial_inertia = plucker.spatial_inertia_matrix_IO(I.ixx, I.ixy, I.ixz, I.iyy, I.iyz, I.izz, link.inertial.mass, link.inertial.origin.xyz)
					spatial_inertias.append(spatial_inertia)

		spatial_inertias.pop(0)
		return spatial_inertias


	def _get_spatial_transforms_and_joint_space(self, q, joint_list):
		"""Helper function for RNEA which calculates spatial transform matrices and motion subspace matrices"""
		i_X_0 = []
		i_X_p = []
		joint_spaces = []
		#joint_space = cs.SX.zeros(6,1)
		i = 0

		for joint in joint_list:
			XT = plucker.XT(joint.origin.xyz, joint.origin.rpy)
			if joint.type == "fixed":
				XJ = plucker.XT(joint.origin.xyz, joint.origin.rpy)

			elif joint.type == "prismatic":
				XJ = plucker.XJ_prismatic(joint.axis, q[i])
				print joint.axis.xyz
				if joint.axis[0] == 1.0:
					joint_space = cs.SX([0, 0, 0, 1, 0, 0])
				elif joint.axis[1] == 1.0:
					joint_space = cs.SX([0, 0, 0, 0, 1, 0])
				elif joint.axis[2] == 1.0:
					joint_space = cs.SX([0, 0, 0, 0, 0, 1])

			elif joint.type in ["revolute", "continuous"]:
				XJ = plucker.XJ_revolute(joint.axis, q[i])
				if joint.axis[0] == 1.0:
					joint_space = cs.SX([1, 0, 0, 0, 0, 0])
				elif joint.axis[1] == 1.0:
					joint_space = cs.SX([0, 1, 0, 0, 0, 0])
				elif joint.axis[2] == 1.0:
					joint_space = cs.SX([0, 0, 1, 0, 0, 0])

			i_X_p.append(cs.mtimes(XJ, XT))
			joint_spaces.append(joint_space)

			if(i == 0):
				i_X_0.append(i_X_p[i])

			else:
				i_X_0.append(cs.mtimes(i_X_p[i], i_X_0[i-1]))
			i += 1

		return i_X_p, i_X_0, joint_spaces



	def _apply_external_forces(external_f, f, i_X_0):
		for i in range(0, len(f)):
			#i_X_0[i] = inv(i_X_0.T)
			f[i] -= cs.mtimes(i_X_0[i], external_f[i])
		return f




	def get_inverse_dynamics_RNEA(self, root, tip, f_ext = None):
		"""Calculates and returns the casadi inverse dynamics, aka tau, using RNEA"""

		if self.robot_desc is None:
			raise ValueError('Robot description not loaded from urdf')

		joint_list = self._get_joint_list(root, tip)
		n_joints = len(joint_list)
		q = cs.SX.sym("q", n_joints)
		q_dot = cs.SX.sym("q_dot", n_joints)
		q_ddot = cs.SX.sym("q_ddot", n_joints)
		i_X_p, i_X_0, joint_space = self._get_spatial_transforms_and_joint_space(q, joint_list)
		Ic = self.get_spatial_inertias(root, tip)
		print "number of bodies:", len(Ic)
		print "number of joints:", n_joints
		v = []
		a = []
		#f = cs.SX.zeros(n_bodies-1)
		f = []
		tau = cs.SX.zeros(n_joints)
		v0 = cs.SX.zeros(6,1)
		a_gravity = cs.SX([0., 0., 0., 0., -9.81, 0.])

		for i in range(0, n_joints):

			#OBS! Boor legge denne i jcalc slik at RNEA ikke er avhengig av jointtype
			if (joint_list[i].type == "fixed"):
				if(i is 0):
					v.append(v0)
					a.append(cs.mtimes(i_X_p[i], -a_gravity))
				else:
					v.append(cs.mtimes(i_X_p[i], v[i-1]))
					a.append(cs.mtimes(i_X_p[i], a[i-1]))
			else:
				vJ = cs.mtimes(joint_space[i],q_dot[i])

				if(i is 0):
					v.append(vJ)
					a.append(cs.mtimes(i_X_p[i], a_gravity) + vJ)
				else:
					v.append(cs.mtimes(i_X_p[i], v[i-1]) + joint_space[i]*q_dot[i])
					a.append(cs.mtimes(i_X_p[i], a[i-1]) + cs.mtimes(joint_space[i],q_ddot[i]) + cs.mtimes(plucker.motion_cross_product(v[i]),vJ))

			f.append(cs.mtimes(Ic[i], a[i]) + cs.mtimes(plucker.motion_cross_product(v[i]), cs.mtimes(Ic[i], v[i])))#dim 6x1

		if f_ext is not None:
			f = self._apply_external_forces(f_ext, f, i_X_0)

		for i in range((n_joints-1), -1, -1):
			tau[i] = cs.mtimes(joint_space[i].T, f[i])
			if (i-1) is not -1:
				f[i-1] = f[i-1] + cs.mtimes(i_X_p[i].T, f[i])

		#must figure f out...
		#for i in range(0, n_bodies-1):
			#tau[i] = cs.Function("tau", [q, q_dot, q_ddot], [tau[i]])
		#f = cs.Function("f", [q, q_dot, q_ddot], [f])

		tau = cs.Function("tau", [q, q_dot, q_ddot], [tau])
		return tau



	#make another one with only root ant tip as input
	def _get_H(self, Ic, i_X_p, joint_space, n_joints):
			"""Returns the joint space inertia matrix aka the H-component of the equation of motion tau = H(q)q_ddot + C(q, q_dot,fx)"""
			H = cs.SX.zeros(n_joints, n_joints)

			#for i in range(0, n_joints-1):
				#Ic[i-1] += cs.mtimes(i_X_p[i].T, cs.mtimes(Ic[i], i_X_p[i]))

			for i in range(n_joints-2, -1, -1):
				if i is not 0:
					Ic[i-1] += cs.mtimes(i_X_p[i].T, cs.mtimes(Ic[i], i_X_p[i]))
				F = cs.mtimes(Ic[i], joint_space[i])
				H[i, i] = cs.mtimes(joint_space[i].T, F)
				j = i
				while j is not 0:
					F = cs.mtimes(i_X_p[j].T, F)
					j -= 1
					H[i,j] = cs.mtimes(F.T, joint_space[j])
					H[j,i] = H[i,j]

			return H

	def get_jointpace_inertia_matrix(self, root, tip):
			"""Returns the joint space inertia matrix aka the H-component of the equation of motion tau = H(q)q_ddot + C(q, q_dot,fx)"""
			if self.robot_desc is None:
				raise ValueError('Robot description not loaded from urdf')


			joint_list = _get_joint_list(root, tip)
			Ic = self.get_spatial_inertias(root, tip)
			n_bodies = len(Ic)
			i_X_p, i_X_0, joint_space = self._get_spatial_transforms_and_joint_space(q, joint_list)
			H = cs.SX.zeros(n_bodies, n_bodies)

			for i in range(n_bodies-2, -1, -1):
				Ic[i-1] += cs.mtimes(i_X_p[i].T, cs.mtimes(Ic[i], i_X_p[i]))

			for i in range(0, n_bodies-1):
				fh = cs.mtimes(Ic[i], joint_space[i])
				H[i, i] = cs.mtimes(joint_space[i].T, fh)
				j = i
				while (j-1) is not -1:
					fh = cs.mtimes(i_X_p[j].T, fh)
					j -= 1
					H[i,j] = cs.mtimes(joint_space[j].T, fh)
					H[j,i] = H[i,j]

			H = cs.Function("H", [q], [H])
			return H


	#make another one with only root and tip as input
	def _get_C(self, joint_list, i_X_p, joint_space, Ic, q, q_dot, n_joints, f_ext = None):
			"""Returns the joint space bias matrix aka the C-component of the equation of motion tau = H(q)q_ddot + C(q, q_dot,fx)"""
			v = []
			a = []
			f = []
			C = cs.SX.zeros(n_joints)
			v0 = cs.SX.zeros(6,1)
			a_gravity = cs.SX([0., 0., 0., 0., 0., 9.81])

			for i in range(0, n_joints-1):
				if (joint_list[i].type == "fixed"):
					if((i-1) is -1):
						v.append(v0)
						a.append(cs.mtimes(i_X_p[i], -a_gravity))
					else:
						v.append(cs.mtimes(i_X_p[i], v[i-1]))
						a.append(cs.mtimes(i_X_p[i], a[i-1]))
				else:
					vJ = cs.mtimes(joint_space[i],q_dot[i])

					if((i-1) is -1):
						v.append(vJ)
						a.append(cs.mtimes(i_X_p[i], -a_gravity))
					else:
						v.append(cs.mtimes(i_X_p[i], v[i-1]) + vJ)
						a.append(cs.mtimes(i_X_p[i], a[i-1]) + cs.mtimes(plucker.motion_cross_product(v[i]),vJ))

				f.append(cs.mtimes(Ic[i], a[i]) + cs.mtimes(plucker.force_cross_product(v[i]), cs.mtimes(Ic[i], v[i])))#dim 6x1

			if f_ext is not None:
				f = self._apply_external_forces(f_ext, f, i_X_0)

			for i in range((n_joints-2), -1, -1):
				C[i] = cs.mtimes(joint_space[i].T, f[i])
	    		#if (i-1) is not 0:
	        		#f[i-1] = f[i-1] + cs.mtimes(i_X_p[i].T, f[i])
			return C


	def get_jointspace_bias_matrix(self, root, tip, f_ext = None):
			"""Returns the joint space bias matrix aka the C-component of the equation of motion tau = H(q)q_ddot + C(q, q_dot,fx)"""
			if self.robot_desc is None:
				raise ValueError('Robot description not loaded from urdf')



			joint_list = self._get_joint_list(root, tip)
			n_joints = len(joint_list)
			q = cs.SX.sym("q", n_joints)
			q_dot = cs.SX.sym("q_dot", n_joints)
			i_X_p, i_X_0, joint_space = self._get_spatial_transforms_and_joint_space(q, joint_list)
			Ic = self.get_spatial_inertias(root, tip)

			for i in range(0, n_joints):
				print joint_space[i]

			v = []
			a = []
			f = []
			C = cs.SX.zeros(n_joints)
			v0 = cs.SX.zeros(6,1)
			a_gravity = cs.SX([0., 0., 0., 0., 0., 9.81])

			for i in range(0, n_joints):
				if (joint_list[i].type == "fixed"):
					if((i-1) is -1):
						v.append(v0)
						a.append(cs.mtimes(i_X_p[i], -a_gravity))
					else:
						v.append(cs.mtimes(i_X_p[i], v[i-1]))
						a.append(cs.mtimes(i_X_p[i], a[i-1]))
				else:
					vJ = cs.mtimes(joint_space[i],q_dot[i])

					if((i-1) is -1):
						v.append(vJ)
						a.append(cs.mtimes(i_X_p[i], -a_gravity))
					else:
						v.append(cs.mtimes(i_X_p[i], v[i-1]) + vJ)
						a.append(cs.mtimes(i_X_p[i], a[i-1]) + cs.mtimes(plucker.motion_cross_product(v[i]),vJ))

				f.append(cs.mtimes(Ic[i], a[i]) + cs.mtimes(plucker.force_cross_product(v[i]), cs.mtimes(Ic[i], v[i])))#dim 6x1

			if f_ext is not None:
				f = self._apply_external_forces(f_ext, f, i_X_0)

			for i in range((n_joints-1), -1, -1):
				C[i] = cs.mtimes(joint_space[i].T, f[i])
	    		#if (i-1) is not 0:
	        		#f[i-1] = f[i-1] + cs.mtimes(i_X_p[i].T, f[i

			C = cs.Function("C", [q, q_dot], [C])
			return C



	def get_forward_dynamics_CRBA(self, root, tip, tau):
			"""Returns the casadi forward dynamics using one of the inertia matrix method - composite rigid body algorithm"""

			if self.robot_desc is None:
				raise ValueError('Robot description not loaded from urdf')

			joint_list = self._get_joint_list(root, tip)
			n_joints = len(joint_list)
			q = cs.SX.sym("q", n_joints)
			q_dot = cs.SX.sym("q_dot", n_joints)
			q_ddot = cs.SX.zeros(n_joints)
			i_X_p, i_X_0, joint_space = self._get_spatial_transforms_and_joint_space(q, joint_list)
			Ic = self.get_spatial_inertias(root, tip)

			H = self._get_H(Ic, i_X_p, joint_space, n_joints)
			H_inv = cs.solve(H, cs.SX.eye(H.size1()))
			C = self._get_C(joint_list, i_X_p, joint_space, Ic, q, q_dot, n_joints)

			q_ddot = cs.mtimes(H_inv, (tau - C))


			q_ddot = cs.Function("q_ddot", [q, q_dot], [q_ddot])
			return q_ddot



	def get_forward_dynamics_ABA(self, root, tip, tau, f_ext = None):
		"""Returns the casadi forward dynamics using the inertia articulated rigid body algorithm"""

		if self.robot_desc is None:
			raise ValueError('Robot description not loaded from urdf')

		joint_list = self._get_joint_list(root, tip)
		n_joints = len(joint_list)
		q = cs.SX.sym("q", n_joints)
		q_dot = cs.SX.sym("q_dot", n_joints)
		q_ddot = cs.SX.zeros(n_joints)
		i_X_p, i_X_0, joint_space = self._get_spatial_transforms_and_joint_space(q, joint_list)
		Ic = self.get_spatial_inertias(root, tip)

		v = []
		c = []
		pA = []

		#Which is better if any?
		#U = cs.SX.zeros(6, n_joints)
		#d = cs.SX.zeros(1, n_joints)
		u = cs.SX.zeros(1, n_joints)
		U = [None]*n_joints
		d = [None]*n_joints
		zeros = cs.SX.zeros(6)

		for i in range(0, n_joints):
			if (joint_list[i].type == "fixed"):
				if((i-1) is -1):
					v.append(zeros)
					c.append(zeros)
				else:
					v.append(cs.mtimes(i_X_p[i], v[i-1]))
					c.append(cs.mtimes(plucker.motion_cross_product(v[i]), vJ))

			else:
				vJ = cs.mtimes(joint_space[i], q_dot[i])
				if i-1 is -1:
					v.append(vJ)
					c.append(cs.SX.zeros(6))
				else:
					v.append(cs.mtimes(i_X_p[i], v[i-1]) + vJ)
					c.append(cs.mtimes(plucker.motion_cross_product(v[i]), vJ))

			pA.append(cs.mtimes(plucker.force_cross_product(v[i]), cs.mtimes(Ic[i], v[i])))

		if f_ext is not None:
			pA = self._apply_external_forces(f_ext, pa)

		for i in range(n_joints-1, -1, -1):
			#U[:6,i] = cs.mtimes(Ic[i], joint_space[i])#6x6 * 6x1 = 6x1
			U[i] = cs.mtimes(Ic[i], joint_space[i])#6x6 * 6x1 = 6x1
			#d[i] = cs.mtimes(joint_space[i].T, U[:6,i])#1x6 x 6x1 = 1x1
			d[i] = cs.mtimes(joint_space[i].T, U[i])
			u[i] = tau[i] - cs.mtimes(joint_space[i].T, pA[i]) # 1x1 - 1x6 x 6x1 = 1x1
			if i-1 is not -1:

				Ia = Ic[i] - (cs.mtimes(U[i], U[i].T)/d[i])
				pa = pA[i] + cs.mtimes(Ic[i], c[i]) + cs.mtimes(U[i], u[i]/d[i])
				Ic[i-1] += cs.mtimes(i_X_p[i].T, cs.mtimes(Ia, i_X_p[i]))
				pA[i-1] += cs.mtimes(i_X_p[i].T, pa)

		a = []
		a_gravity = cs.SX([0., 0., 0., 0., -9.81, 0.])

		for i in range(0, n_joints):
			if i is 0:
				a_temp = (cs.mtimes(i_X_p[i], a_gravity) + c[i])#6x1
			else:
				a_temp = (cs.mtimes(i_X_p[i], a[i-1]) + c[i])#6x1

			if joint_list[i].type is "fixed":
				a.append(a_temp)

			else:
				#q_ddot[i] = u[i] - (cs.mtimes(U[:6,i].T, a_temp)/d[i])
				q_ddot[i] = u[i] - (cs.mtimes(U[i].T, a_temp)/d[i])
				a.append(a_temp + cs.mtimes(joint_space[i], q_ddot[i]))#6x1

		q_ddot = cs.Function("q_ddot", [q, q_dot], [q_ddot])
		return q_ddot




	def get_forward_kinematics(self, root, tip):
		"""Using one of the above to derive info needed for casadi fk"""
		chain = self.robot_desc.get_chain(root, tip)
		#if self.robot_desc is None:
			#raise ValueError('Robot description not loaded from urdf')
		joint_list, nvar, actuated_names, upper, lower = self.get_joint_info(root, tip)

		#make symbolics
		T_fk = cs.SX.eye(4)
		q = cs.SX.sym("q", nvar)
		quaternion_fk = cs.SX.zeros(4)
		quaternion_fk[3] = 1.0
		dual_quaternion_fk = cs.SX.zeros(8)
		dual_quaternion_fk[3] = 1.0
		i = 0
		for joint in joint_list:
			if joint.type == "fixed":
				xyz = joint.origin.xyz
				rpy = joint.origin.rpy
				joint_frame = T.numpy_rpy(xyz, *rpy)
				joint_quaternion = quaternion.numpy_rpy(*rpy)
				joint_dual_quat = dual_quaternion.numpy_prismatic(xyz,
				                                           rpy,
				                                           [1., 0., 0.],
				                                           0.)
				T_fk = cs.mtimes(T_fk, joint_frame)
				quaternion_fk = quaternion.product(quaternion_fk,
				                                   joint_quaternion)
				dual_quaternion_fk = dual_quaternion.product(
				dual_quaternion_fk,
				joint_dual_quat)

			elif joint.type == "prismatic":
				if joint.axis is None:
					axis = cs.np.array([1., 0., 0.])
				else:
					axis = cs.np.array(joint.axis)
	            #axis = (1./cs.np.linalg.norm(axis))*axis
				joint_frame = T.prismatic(joint.origin.xyz,
				                                  joint.origin.rpy,
				                                  joint.axis, q[i])
				joint_quaternion = quaternion.numpy_rpy(*joint.origin.rpy)
				joint_dual_quat = dual_quaternion.prismatic(
				joint.origin.xyz,
				joint.origin.rpy,
				axis, q[i])
				T_fk = cs.mtimes(T_fk, joint_frame)
				quaternion_fk = quaternion.product(quaternion_fk,
				                                           joint_quaternion)
				dual_quaternion_fk = dual_quaternion.product(dual_quaternion_fk, joint_dual_quat)
				i += 1

			elif joint.type in ["revolute", "continuous"]:
				if joint.axis is None:
					axis = cs.np.array([1., 0., 0.])
				else:
					axis = cs.np.array(joint.axis)
				axis = (1./cs.np.linalg.norm(axis))*axis
				joint_frame = T.revolute(joint.origin.xyz, joint.origin.rpy, joint.axis, q[i])
				joint_quaternion = quaternion.revolute(joint.origin.xyz, joint.origin.rpy, axis, q[i])
				joint_dual_quat = dual_quaternion.revolute(joint.origin.xyz, joint.origin.rpy, axis, q[i])
				T_fk = cs.mtimes(T_fk, joint_frame)
				quaternion_fk = quaternion.product(quaternion_fk, joint_quaternion)
				dual_quaternion_fk = dual_quaternion.product(dual_quaternion_fk,joint_dual_quat)
				i += 1

		T_fk = cs.Function("T_fk", [q], [T_fk])
		quaternion_fk = cs.Function("quaternion_fk", [q], [quaternion_fk])
		dual_quaternion_fk = cs.Function("dual_quaternion_fk", [q], [dual_quaternion_fk])

		return {
		    "joint_names": actuated_names,
		    "upper": upper,
		    "lower": lower,
		    "joint_list": joint_list,
		    "q": q,
		    "quaternion_fk": quaternion_fk,
		    "dual_quaternion_fk": dual_quaternion_fk,
		    "T_fk": T_fk
		}
