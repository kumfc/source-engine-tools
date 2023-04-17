from dataclasses import dataclass
from enum import IntEnum
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from utils import *


def get_vert_count(power):
    return ((1 << power) + 1) * ((1 << power) + 1)


def get_post_spacing(power):
    return (1 << power) + 1


class DispOrientation(IntEnum):
    HORIZONTAL_DOWN = 0  # -Z
    HORIZONTAL = 1  # Z
    VERTICAL_SOUTH = 2  # -Y
    VERTICAL_NORTH = 3  # Y
    VERTICAL_WEST = 4  # -X
    VERTICAL_EAST = 5  # X


class SurfaceVert:
    def __init__(self, idx: int, coord: np.array, post_spacing, plane, orientation):
        self.idx = idx
        self.post_spacing = post_spacing
        self.idx_from_edge = idx % post_spacing
        self.coord = coord
        self.disp_plane = plane
        self.disp_orientation = orientation

        self.ancestor_vert = None
        self.child_vert = None
        self.prev_neighbour_vert = None
        self.next_neighbour_vert = None

        self.edge_to_child = None
        self.edge_to_next = None

        self.edges = set()
        self.triangles = set()

    def set_neighbours(self, surface):
        if self.idx > 0 and not self.is_on_primary_edge():
            self.ancestor_vert = surface[self.idx - 1]

        if not self.is_on_secondary_edge():
            self.child_vert = surface[self.idx + 1]
            self.edge_to_child = SurfaceEdge(self, self.child_vert)

        if self.idx >= self.post_spacing:
            self.prev_neighbour_vert = surface[self.idx - self.post_spacing]

        try:
            self.next_neighbour_vert = surface[self.idx + self.post_spacing]
            self.edge_to_next = SurfaceEdge(self, self.next_neighbour_vert)
        except IndexError:
            pass

    @property
    def distance_from_plane(self):
        orientation_cf = -1 if self.disp_orientation in [DispOrientation.VERTICAL_SOUTH, DispOrientation.VERTICAL_WEST] else 1
        return np.dot(self.coord, self.disp_plane.normal) + self.disp_plane.dist / np.linalg.norm(self.disp_plane.normal) * orientation_cf

    def is_first_corner(self):
        return self.idx == 0

    def is_second_corner(self):
        return self.idx == (self.post_spacing - 1)

    def is_third_corner(self):
        return self.idx == (self.post_spacing ** 2 - self.post_spacing)

    def is_fourth_corner(self):
        return self.idx == (self.post_spacing ** 2 - 1)

    def is_on_first_descending_edge(self):
        return self.idx < self.post_spacing

    def is_on_last_descending_edge(self):
        return self.idx > (self.post_spacing ** 2 - self.post_spacing - 1)

    def is_on_primary_edge(self):
        return self.idx % self.post_spacing == 0

    def is_on_secondary_edge(self):
        return (self.idx + 1) % self.post_spacing == 0

    def __repr__(self):
        return str(self.coord)

    def __getitem__(self, item):
        return self.coord[item]

    def __mul__(self, other):
        if type(other) == SurfaceVert:
            return self.coord * other.coord
        else:
            return self.coord * other

    def __sub__(self, other):
        if type(other) == SurfaceVert:
            return self.coord - other.coord
        else:
            return self.coord - other


class SurfaceEdge:
    def __init__(self, start, end, tr=False):
        self.start = start
        self.end = end
        self.is_tr_edge = tr

        start.edges.add(self)
        end.edges.add(self)

        self.triangles = set()

    def __repr__(self):
        return str([self.start, self.end])

    def is_ceiling(self, disp_orientation):
        if disp_orientation == DispOrientation.HORIZONTAL:
            return False, 0, 0
        elif disp_orientation == DispOrientation.HORIZONTAL_DOWN:
            return True, -1, -1

        if abs(self.start.coord[2] - self.end.coord[2]) < 0.4 * abs(np.linalg.norm(self.start.coord - self.end.coord)):
            return False, 0, 0

        if self.start.coord[2] > self.end.coord[2]:
            high, low = self.start.distance_from_plane, self.end.distance_from_plane
        else:
            high, low = self.end.distance_from_plane, self.start.distance_from_plane

        return high > low, high, low


class Triangle:
    def __init__(self, edges):
        self.color = '#4287F5'
        self.edges = set()
        self.__verts = set()

        for edge in edges:
            self.edges.add(edge)
            self.__verts.add(edge.start)
            self.__verts.add(edge.end)
            edge.triangles.add(self)
            edge.start.triangles.add(self)
            edge.end.triangles.add(self)

    @property
    def verts(self):
        return list(self.__verts)

    @property
    def np_verts(self):
        return np.array(list(map(lambda e: e.coord, self.__verts)))

    def __repr__(self):
        return str(list(self.verts))

    def reset_color(self):
        self.color = '#4287f5'


@dataclass
class Plane:
    id: int
    normal: np.array
    dist: float
    type: int

    def __init__(self, plane_id, bsp_data):
        plane = bsp_data.m_planes[plane_id]

        self.id = plane_id
        self.normal = Vector(plane.normal)
        self.dist = plane.dist
        self.type = plane.type


class Displacement:
    def __init__(self, idx, bsp_data):
        disp = bsp_data.m_displacements[idx]
        self.idx = idx
        self.__disp_info = disp
        self.power = disp.power
        assert 2 <= self.power <= 4
        self.vert_count = get_vert_count(self.power)
        self.post_spacing = get_post_spacing(self.power)
        self.start_vert = disp.dispVertStart
        self.start_position = Vector(disp.startPosition)
        self.map_face_id = disp.mapFace
        self.map_face = bsp_data.m_faces[self.map_face_id]
        self.map_surface_edge_ids = bsp_data.m_surf_edges[self.map_face.firstedge:self.map_face.firstedge+4]
        self.map_plane = Plane(self.map_face.planenum, bsp_data)

        self.orientation = self.__get_orientation()
        self.face_verts = self.__get_face_verts(bsp_data)
        self.verts = bsp_data.m_displacement_verts[self.start_vert:self.start_vert + self.vert_count]
        self.surface = self.__get_surface_verts()

        self.__build_inheritance()

        self.surface_edges, self.triangles = self.__triangulate()

    def get_facing_setpos(self):
        center = np.mean(self.face_verts, axis=0)
        offset = self.map_plane.normal * 200

        pos = center + offset
        ang = calculate_camera_rotation(-(offset + np.array([0, 0, 83])))

        return f'setpos {pos[0]} {pos[1]} {pos[2]}; setang {ang[0]} {ang[1]} 0'

    def __build_inheritance(self):
        for vert in self.surface:
            vert.set_neighbours(self.surface)

    def __triangulate(self):
        edges = set()
        triangles = list()
        for vert in self.surface:
            if vert.idx % 2 == 0:
                if not vert.is_on_last_descending_edge():
                    if vert.child_vert:
                        tr_edge = SurfaceEdge(vert, self.surface[vert.idx + self.post_spacing + 1], True)
                        sus_1 = {vert.edge_to_next, vert.next_neighbour_vert.edge_to_child, tr_edge}
                        sus_2 = {vert.edge_to_child, vert.child_vert.edge_to_next, tr_edge}
                        triangles += [Triangle(sus_1), Triangle(sus_2)]
                        edges.update(sus_1)
                        edges.update(sus_2)
                    if vert.ancestor_vert:
                        tr_edge = SurfaceEdge(vert, self.surface[vert.idx + self.post_spacing - 1], True)
                        sus_1 = {vert.ancestor_vert.edge_to_next, vert.ancestor_vert.edge_to_child, tr_edge}
                        sus_2 = {vert.edge_to_next, vert.next_neighbour_vert.ancestor_vert.edge_to_child, tr_edge}
                        triangles += [Triangle(sus_1), Triangle(sus_2)]
                        edges.update(sus_1)
                        edges.update(sus_2)

        return edges, triangles

    def __get_orientation(self):
        axis = self.map_plane.type % 3
        if axis == 0:
            return DispOrientation.VERTICAL_EAST if self.map_plane.normal[0] > 0 else DispOrientation.VERTICAL_WEST
        elif axis == 1:
            return DispOrientation.VERTICAL_NORTH if self.map_plane.normal[1] > 0 else DispOrientation.VERTICAL_SOUTH
        else:
            return DispOrientation.HORIZONTAL if self.map_plane.normal[2] > 0 else DispOrientation.HORIZONTAL_DOWN

    def __get_face_verts(self, bsp_data):
        face_verts = [Vector(bsp_data.m_verts[bsp_data.m_edges[-idx].v[1] if idx < 0 else bsp_data.m_edges[idx].v[0]]) for idx in self.map_surface_edge_ids]

        dist = np.linalg.norm(face_verts[0] - self.start_position)
        idx = 0
        for i in range(1, 4):
            n_dist = np.linalg.norm(face_verts[i] - self.start_position)
            if n_dist < dist:
                dist = n_dist
                idx = i

        for i in range(idx):
            list_rot(face_verts)

        return face_verts

    def __get_surface_verts(self):
        surface = []

        points = self.face_verts
        ooInt = 1.0 / (self.post_spacing - 1)

        edge_intervals = [
            (points[1] - points[0]) * ooInt,
            (points[2] - points[3]) * ooInt
        ]

        for i in range(self.post_spacing):
            endpoints = [
                edge_intervals[0] * i + points[0],
                edge_intervals[1] * i + points[3],
            ]

            segInt = (endpoints[1] - endpoints[0]) * ooInt

            for j in range(self.post_spacing):
                idx = i * self.post_spacing + j
                vert = self.verts[idx]

                flat_vert = endpoints[0] + (segInt * j)
                r_vert = SurfaceVert(idx, flat_vert + Vector(vert.vector) * vert.dist, self.post_spacing, self.map_plane, self.orientation)
                surface.append(r_vert)

        return surface

    def draw_triangulated(self, colormap='y', draw_axis=False, save_to=None, close=True):
        x, y, z = zip(*self.surface)

        zoom_factor = 45

        angle = (35, 30)  # horizontal
        if self.orientation == DispOrientation.VERTICAL_SOUTH:
            angle = (17, -72)
        elif self.orientation == DispOrientation.VERTICAL_NORTH:
            angle = (17, 72)
        elif self.orientation == DispOrientation.VERTICAL_EAST:
            angle = (10, 15)
        elif self.orientation == DispOrientation.VERTICAL_WEST:
            angle = (10, -160)

        ax = plt.figure().add_subplot(projection='3d')

        for i in range(len(self.triangles)):
            tr_x, tr_y, tr_z = zip(*self.triangles[i].verts)

            verts = [list(zip(tr_x, tr_y, tr_z))]
            srf = Poly3DCollection(verts, alpha=0.90, facecolor=self.triangles[i].color)
            plt.gca().add_collection3d(srf)

        ax.scatter(x, y, z, c=colormap, marker='o', s=40)

        ax.set_xlim3d(min(x) + zoom_factor, max(x) - zoom_factor)
        ax.set_ylim3d(min(y) + zoom_factor, max(y) - zoom_factor)
        ax.set_zlim3d(min(z) + zoom_factor, max(z) - zoom_factor)

        ax.set_aspect('equal')
        if not draw_axis:
            plt.axis('off')
        ax.view_init(*angle)

        if save_to:
            plt.savefig(save_to)
        else:
            plt.show()

        if close:
            plt.close()

    def draw_old(self, colormap='y', with_world_face=False, draw_axis=False):  # replaced by properly triangulated draw_surface
        x, y, z = zip(*self.surface)

        angle = (35, 30)  # horizontal
        if self.orientation == DispOrientation.VERTICAL_SOUTH:
            x, y, z = z, x, y
            angle = (-60, 60, -60)
        elif self.orientation == DispOrientation.VERTICAL_NORTH:
            x, y, z = z, list_neg(x), list_neg(y)
            angle = (-55, 60, -60)
        elif self.orientation == DispOrientation.VERTICAL_EAST:
            x, y, z = list_neg(y), z, list_neg(x)
            angle = (-80, 90)
        elif self.orientation == DispOrientation.VERTICAL_WEST:
            x, y, z = y, z, x
            angle = (-90, 90)

        zoom_factor = 45

        ax = plt.figure().add_subplot(projection='3d')
        ax.plot_trisurf(x, y, z, linewidth=0.2, antialiased=True, cmap='coolwarm')

        ax.scatter(x, y, z, c=colormap, marker='o', s=40)

        if with_world_face:
            wx, wy, wz = zip(*self.face_verts)
            if self.orientation == DispOrientation.VERTICAL_NORTH:
                wx, wy, wz = wz, wx, wy

            ax.scatter(wx, wy, wz, c=['green', 'blue', 'blue', 'blue'], marker='v', s=60)
            ax.scatter([self.start_position[0]], [self.start_position[1]], [self.start_position[2]], c='purple', marker='x', s=100)

        ax.set_xlim3d(min(x) + zoom_factor, max(x) - zoom_factor)
        ax.set_ylim3d(min(y) + zoom_factor, max(y) - zoom_factor)
        ax.set_zlim3d(min(z) + zoom_factor, max(z) - zoom_factor)

        ax.set_aspect('equal')
        if not draw_axis:
            plt.axis('off')
        ax.view_init(*angle)
        plt.show()
