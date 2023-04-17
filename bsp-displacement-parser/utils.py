import numpy as np
import math


def angle_bc(plane1, plane2):
    planes = np.concatenate((plane1[:2]-plane1[2], plane2[:2]-plane2[2]), axis=0)
    a = (planes@planes.T).ravel().tolist()
    return np.degrees(math.acos((a[2]*a[7]-a[3]*a[6]) / math.sqrt((a[0]*a[5]-a[1]*a[1])*(a[10]*a[15]-a[11]*a[11]))))


def list_rot(lst):
    lst.append(lst.pop(0))


def list_neg(lst):
    return [-e for e in lst]


def calculate_camera_rotation(vec):
    if vec[0] == 0 and vec[1] == 0:
        yaw = 0
        pitch = 270 if vec[2] else 90
    else:
        yaw = np.degrees(np.arctan2(vec[1], vec[0]))
        pitch = np.degrees(np.arctan2(-vec[2], math.sqrt(vec[0] * vec[0] + vec[1] * vec[1])))

    return pitch, yaw


def unit_vector(vector):
    return vector / np.linalg.norm(vector)


def Vector(vec):
    return np.array([vec.x, vec.y, vec.z])