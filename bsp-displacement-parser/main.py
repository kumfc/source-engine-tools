import numpy as np
import random
from string import ascii_lowercase, digits
from valvebsp import Bsp
from valvebsp.lumps import *

from displacement import Displacement, DispOrientation
from md_report import MarkdownReport
from utils import angle_bc


# untested
TF_PLAYER = 83
TF_PLAYER_DUCKING = 63
TF_SENTRY_LVL3_HEIGHT = 87
TF_DISPENSER_HEIGHT = 83
TF_TELEPORT_HEIGHT = 12


class Criteria:
    min_height = TF_PLAYER_DUCKING
    min_plane_dist_diff = 8
    min_angle = 150
    max_angle = 170


class BspData:
    def __init__(self, bsp):
        self.m_displacements = bsp[LUMP_DISPINFO]
        self.m_displacement_verts = bsp[LUMP_DISP_VERTS]
        self.m_planes = bsp[LUMP_PLANES]
        self.m_faces = bsp[LUMP_FACES]
        self.m_surf_edges = bsp[LUMP_SURFEDGES]
        self.m_edges = bsp[LUMP_EDGES]
        self.m_verts = bsp[LUMP_VERTEXES]


def edge_vector(edge):
    return edge.end - edge.start


def tris_ang(tris):
    tr_1 = tris[0].np_verts
    tr_2 = tris[1].np_verts

    ang = angle_bc(tr_1, tr_2)

    if ang < 90:
        ang = 180 - ang

    return ang


def rand_img_name():
    return ''.join(random.choices(ascii_lowercase + digits, k=10)) + '.jpg'


def main(map_name):
    bsp = Bsp(f'maps/{map_name}.bsp', 'TF2')
    bsp_data = BspData(bsp)

    md = MarkdownReport(map_name, len(bsp_data.m_displacements), len(bsp_data.m_displacement_verts))

    for i in range(0, len(bsp_data.m_displacements)):
        try:
            disp = Displacement(i, bsp_data)
        except AssertionError:
            print(f'[Parse Error] {i} Bad disp, unpack first?, power = {bsp_data.m_displacements[i].power}')
            continue

        if disp.orientation in [DispOrientation.HORIZONTAL, DispOrientation.HORIZONTAL_DOWN]:
            continue

        print(f'[IDX] {i}')
        heading_added = False

        surface = disp.surface
        for edge in disp.surface_edges:
            if edge.is_tr_edge or len(edge.triangles) != 2:
                continue

            is_ceiling, high, low = edge.is_ceiling(disp.orientation)
            diff = abs(high - low)
            if not is_ceiling:
                continue

            colormap = ['r' if e.idx in [edge.start.idx, edge.end.idx] else 'y' for e in surface]
            edge_vec = edge_vector(edge)
            tris = list(edge.triangles)
            try:
                ang = tris_ang(tris)
            except:
                ang = -1

            if diff < Criteria.min_plane_dist_diff or not (Criteria.min_angle < ang < Criteria.max_angle) or abs(edge_vec[2]) < Criteria.min_height:
                continue

            other_verts = (set(tris[0].verts) | set(tris[1].verts)) - {edge.start, edge.end}

            print(other_verts)
            print(high)
            print(list(other_verts)[0].distance_from_plane)
            print(list(other_verts)[1].distance_from_plane)

            for b in tris:
                b.color = 'r'

            img_name = f'reports/images/{map_name}/{rand_img_name()}'
            disp.draw_triangulated(colormap=colormap, save_to=img_name)

            if not heading_added:
                md.next_displacement(i, disp.get_facing_setpos())
                heading_added = True
            md.add_spot(img_name, ang, diff, abs(edge_vec[2]))

            for b in tris:
                b.reset_color()

    md.save()


def main_interactive(map_name, index):
    bsp = Bsp(f'maps/{map_name}.bsp', 'TF2')
    bsp_data = BspData(bsp)

    disp = Displacement(index, bsp_data)
    print(disp.orientation)
    print('[SETPOS] ', disp.get_facing_setpos())
    disp.draw_triangulated(close=False)


if __name__ == '__main__':
    main('disp_test_onlybroken')
