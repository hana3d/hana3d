# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####
import json
import logging
import math
import sys
from importlib import import_module
from pathlib import Path

import bpy
import mathutils

HANA3D_NAME = sys.argv[-1]
HANA3D_EXPORT_TEMP_DIR = sys.argv[-2]
HANA3D_THUMBNAIL_PATH = sys.argv[-3]
HANA3D_EXPORT_FILE_INPUT = sys.argv[-4]
HANA3D_EXPORT_DATA = sys.argv[-5]

module = import_module(HANA3D_NAME)
append_link = module.append_link
bg_blender = module.bg_blender
utils = module.utils


def get_obnames():
    with open(HANA3D_EXPORT_DATA, 'r') as s:
        data = json.load(s)
    obnames = eval(data['models'])
    return obnames


def center_obs_for_thumbnail(obs):
    s = bpy.context.scene
    # obs = bpy.context.selected_objects
    parent = obs[0]

    while parent.parent is not None:
        parent = parent.parent
    # reset parent rotation, so we see how it really snaps.
    parent.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    minx, miny, minz, maxx, maxy, maxz = utils.get_bounds_worldspace(obs)

    cx = (maxx - minx) / 2 + minx
    cy = (maxy - miny) / 2 + miny
    for ob in s.collection.objects:
        ob.select_set(False)

    bpy.context.view_layer.objects.active = parent
    parent.location += mathutils.Vector((-cx, -cy, -minz))

    camZ = s.camera.parent.parent
    camZ.location.z = (maxz - minz) / 2
    dx = maxx - minx
    dy = maxy - miny
    dz = maxz - minz
    r = math.sqrt(dx * dx + dy * dy + dz * dz)

    scaler = bpy.context.view_layer.objects['scaler']
    scaler.scale = (r, r, r)
    coef = 0.7
    r *= coef
    camZ.scale = (r, r, r)
    bpy.context.view_layer.update()


if __name__ == "__main__":
    try:
        logging.info('autothumb_model_bg')
        with open(HANA3D_EXPORT_DATA, 'r') as s:
            data = json.load(s)

        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

        bg_blender.progress('preparing thumbnail scene')
        obnames = get_obnames()
        link = not data['save_only']
        main_object, allobs = append_link.append_objects(
            file_name=HANA3D_EXPORT_FILE_INPUT,
            obnames=obnames,
            link=link,
        )
        bpy.context.view_layer.update()

        camdict = {
            'GROUND': 'camera ground',
            'WALL': 'camera wall',
            'CEILING': 'camera ceiling',
            'FLOAT': 'camera float',
        }

        bpy.context.scene.camera = bpy.data.objects[camdict[data['thumbnail_snap_to']]]
        center_obs_for_thumbnail(allobs)
        if user_preferences.thumbnail_use_gpu:
            bpy.context.scene.cycles.device = 'GPU'

        fdict = {
            'DEFAULT': 1,
            'FRONT': 2,
            'SIDE': 3,
            'TOP': 4,
        }
        s = bpy.context.scene
        s.frame_set(fdict[data['thumbnail_angle']])

        snapdict = {'GROUND': 'Ground', 'WALL': 'Wall', 'CEILING': 'Ceiling', 'FLOAT': 'Float'}

        collection = bpy.context.scene.collection.children[snapdict[data['thumbnail_snap_to']]]
        collection.hide_viewport = False
        collection.hide_render = False
        collection.hide_select = False

        main_object.rotation_euler = (0, 0, 0)
        # material declared on thumbnailer.blend
        bpy.data.materials['hana3d background'].node_tree.nodes['Value'].outputs[
            'Value'
        ].default_value = data['thumbnail_background_lightness']
        s.cycles.samples = data['thumbnail_samples']
        bpy.context.view_layer.cycles.use_denoising = data['thumbnail_denoising']
        bpy.context.view_layer.update()

        # import blender's HDR here
        hdr_path = Path('datafiles/studiolights/world/interior.exr')
        bpath = Path(bpy.utils.resource_path('LOCAL'))
        ipath = bpath / hdr_path
        ipath = str(ipath)

        # this  stuff is for mac and possibly linux. For blender // means relative path.
        # for Mac, // means start of absolute path
        if ipath.startswith('//'):
            ipath = ipath[1:]

        hdr_img = bpy.data.images['interior.exr']
        hdr_img.filepath = ipath
        hdr_img.reload()

        bpy.context.scene.render.resolution_x = int(data['thumbnail_resolution'])
        bpy.context.scene.render.resolution_y = int(data['thumbnail_resolution'])

        if data['save_only']:
            hdr_img.pack()
            bpy.ops.wm.save_as_mainfile(filepath=data['blend_filepath'], compress=True, copy=True)
        else:
            bpy.context.scene.render.filepath = HANA3D_THUMBNAIL_PATH
            bg_blender.progress('rendering thumbnail')
            bpy.ops.render.render(write_still=True, animation=False)
        bg_blender.progress('background autothumbnailer finished successfully')

    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)
