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

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from . import utils
from .config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_PROFILE
from .report_tools import execute_wrapper
from .src.search import search
from .src.unified_props import Unified
from .src.upload import upload


class Hana3DAddTag(Operator):
    """Add Tag"""

    bl_idname = f"object.{HANA3D_NAME}_add_tag"
    bl_label = f"Add new tag to {HANA3D_DESCRIPTION}"
    bl_options = {'REGISTER', 'INTERNAL'}

    tag: StringProperty(name='New Tag', default='')

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'tag')

    @execute_wrapper
    def execute(self, context):
        unified_props = Unified(context).props
        props = upload.get_upload_props()
        current_workspace = unified_props.workspace

        new_tag = props.tags_list.add()
        new_tag['name'] = self.tag
        new_tag.selected = True

        search_props = search.get_search_props()
        new_tag = search_props.tags_list.add()
        new_tag['name'] = self.tag

        for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
            if current_workspace == workspace['id']:
                utils.append_array_inside_prop(workspace, 'tags', self.tag)
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


class RemoveTagSearch(Operator):
    """Remove Tag"""

    bl_idname = f"object.{HANA3D_NAME}_remove_tag_search"
    bl_label = f"{HANA3D_DESCRIPTION} List Libraries"
    bl_options = {'REGISTER', 'INTERNAL'}

    tag: bpy.props.StringProperty(name='Tag', default='')

    @execute_wrapper
    def execute(self, context):
        search_props = search.get_search_props()
        search_props.tags_list[self.tag].selected = False
        return {'INTERFACE'}


class RemoveTagUpload(Operator):
    """Remove Tag"""

    bl_idname = f"object.{HANA3D_NAME}_remove_tag_upload"
    bl_label = f"{HANA3D_DESCRIPTION} Remove Tag"
    bl_options = {'REGISTER', 'INTERNAL'}

    tag: bpy.props.StringProperty(name='Tag', default='')

    @execute_wrapper
    def execute(self, context):
        props = upload.get_upload_props()
        props.tags_list[self.tag].selected = False
        return {'INTERFACE'}


classes = (
    Hana3DAddTag,
    RemoveTagSearch,
    RemoveTagUpload
)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
