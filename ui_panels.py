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
from bpy.types import Panel

from . import addon_updater_ops, utils
from .config import (
    HANA3D_DESCRIPTION,
    HANA3D_MATERIALS,
    HANA3D_MODELS,
    HANA3D_NAME,
    HANA3D_RENDER,
    HANA3D_SCENES,
    HANA3D_UI,
)
from .src.panels.download import Hana3DDownloadPanel
from .src.panels.render import Hana3DRenderPanel
from .src.panels.updater import Hana3DUpdaterPanel
from .src.search.search import Search


def label_multiline(layout, text='', icon='NONE', width=-1):
    ''' draw a ui label, but try to split it in multiple lines.'''
    if text.strip() == '':
        return
    lines = text.split('\n')
    if width > 0:
        threshold = int(width / 5.5)
    else:
        threshold = 35
    maxlines = 8
    li = 0
    for line in lines:
        while len(line) > threshold:
            i = line.rfind(' ', 0, threshold)
            if i < 1:
                i = threshold
            l1 = line[:i]
            layout.label(text=l1, icon=icon)
            icon = 'NONE'
            line = line[i:].lstrip()
            li += 1
            if li > maxlines:
                break
        if li > maxlines:
            break
        layout.label(text=line, icon=icon)
        icon = 'NONE'


def prop_needed(layout, props, name, value, is_not_filled=''):
    row = layout.row()
    if value == is_not_filled:
        row.alert = True
        row.prop(props, name)
        row.alert = False
    else:
        row.prop(props, name)
    return row


def draw_selected_tags(layout, props, operator):
    row = layout.row()
    row.scale_y = 0.9
    tag_counter = 0
    for tag in props.tags_list.keys():
        if props.tags_list[tag].selected is True:
            op = row.operator(operator, text=tag, icon='X')
            op.tag = tag
            tag_counter += 1
        if tag_counter == 3:
            row = layout.row()
            row.scale_y = 0.9
            tag_counter = 0


def draw_selected_libraries(layout, props, operator):
    row = layout.row()
    row.scale_y = 0.9
    library_counter = 0
    for library in props.libraries_list.keys():
        if props.libraries_list[library].selected is True:
            op = row.operator(operator, text=library, icon='X')
            op.library = library
            library_counter += 1
        if library_counter == 3:
            row = layout.row()
            row.scale_y = 0.9
            library_counter = 0


def draw_panel_common_upload(layout, context):
    uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
    asset_type = uiprops.asset_type
    props = utils.get_upload_props()

    box = layout.box()
    box.label(text='Workspace and Lib', icon='ASSET_MANAGER')
    box.prop(props, 'workspace', expand=False, text='Workspace')
    row = box.row()
    row.prop_search(props, "libraries_input", props, "libraries_list", icon='VIEWZOOM')
    row.operator(f'object.{HANA3D_NAME}_refresh_libraries', text='', icon='FILE_REFRESH')
    draw_selected_libraries(box, props, f"object.{HANA3D_NAME}_remove_library_upload")
    for name in props.custom_props.keys():
        box.prop(props.custom_props, f'["{name}"]')

    box = layout.box()
    box.label(text='Asset Info', icon='MESH_CUBE')
    row = prop_needed(box, props, 'name', props.name)
    row.operator(f'object.{HANA3D_NAME}_share_asset', text='', icon='LINKED')
    col = box.column()
    if props.is_generating_thumbnail:
        col.enabled = False
    row = col.row(align=True)
    prop_needed(row, props, 'thumbnail', props.has_thumbnail, False)
    if bpy.context.scene.render.engine in ('CYCLES', 'BLENDER_EEVEE'):
        if asset_type == 'MODEL':
            row.operator(f'object.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
        elif asset_type == 'SCENE':
            row.operator(f'scene.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
        elif asset_type == 'MATERIAL':
            row.operator(f'material.{HANA3D_NAME}_thumbnail', text='', icon='IMAGE_DATA')
    if props.is_generating_thumbnail or props.thumbnail_generating_state != '':
        row = box.row()
        row.label(text=props.thumbnail_generating_state)
        if props.is_generating_thumbnail:
            op = row.operator(f'object.{HANA3D_NAME}_kill_bg_process', text="", icon='CANCEL')
            op.process_source = asset_type
            op.process_type = 'THUMBNAILER'
    box.prop(props, 'description')
    # box.prop(props, 'is_public')  # Commented out until feature is needed

    box = layout.box()
    box.label(text='Tags', icon='COLOR')
    row = box.row(align=True)
    row.prop_search(props, "tags_input", props, "tags_list", icon='VIEWZOOM')
    op = row.operator(f'object.{HANA3D_NAME}_add_tag', text='', icon='ADD')
    draw_selected_tags(box, props, f"object.{HANA3D_NAME}_remove_tag_upload")

    prop_needed(layout, props, 'publish_message', props.publish_message)

    if props.upload_state != '':
        label_multiline(layout, text=props.upload_state, width=context.region.width)
    if props.uploading:
        op = layout.operator(f'object.{HANA3D_NAME}_kill_bg_process', text="", icon='CANCEL')
        op.process_source = asset_type
        op.process_type = 'UPLOAD'
        box = box.column()
        box.enabled = False

    row = layout.row()
    row.scale_y = 2.0
    if props.view_id == '' or props.workspace != props.view_workspace:
        optext = 'Upload %s' % asset_type.lower()
        op = row.operator(f"object.{HANA3D_NAME}_upload", text=optext, icon='EXPORT')
        op.asset_type = asset_type

    if props.view_id != '' and props.workspace == props.view_workspace:
        op = row.operator(f"object.{HANA3D_NAME}_upload", text='Reupload asset', icon='EXPORT')
        op.asset_type = asset_type
        op.reupload = True

        op = row.operator(f"object.{HANA3D_NAME}_upload", text='Upload as new asset', icon='EXPORT')
        op.asset_type = asset_type
        op.reupload = False

        layout.label(text='asset has a version online.')


def draw_panel_common_search(layout, context):
    uiprops = getattr(bpy.context.window_manager, HANA3D_UI)
    asset_type = uiprops.asset_type

    search = Search(context)
    search_props = search.props

    row = layout.row()
    row.prop(search_props, 'search_keywords', text='', icon='VIEWZOOM')
    draw_assetbar_show_hide(row, search_props)
    layout.prop(search_props, 'workspace', expand=False, text='Workspace')
    row = layout.row()
    row.prop_search(search_props, 'libraries_input', search_props, 'libraries_list', icon='VIEWZOOM') # noqa : E501
    row.operator(f'object.{HANA3D_NAME}_refresh_libraries', text='', icon='FILE_REFRESH')
    draw_selected_libraries(layout, search_props, f'object.{HANA3D_NAME}_remove_library_search')
    layout.prop_search(search_props, 'tags_input', search_props, 'tags_list', icon='VIEWZOOM')
    draw_selected_tags(layout, search_props, f'object.{HANA3D_NAME}_remove_tag_search')
    layout.prop(search_props, 'public_only')
    label_multiline(layout, text=search_props.report)

    if asset_type == 'MODEL':
        layout.separator()
        layout.label(text='Import method:')
        layout.prop(search_props, 'append_method', expand=True, icon_only=False)
        row = layout.row(align=True)
        row.operator(f'scene.{HANA3D_NAME}_batch_download')
    # elif asset_type == 'SCENE':  # TODO uncomment after fixing scene merge
    #     layout.separator()
    #     layout.label(text='Import method:')
    #     layout.prop(props, 'merge_add', expand=True, icon_only=False)
    #     if props.merge_add == 'MERGE':
    #         layout.prop(props, 'import_world')
    #         layout.prop(props, 'import_render')
    #         layout.prop(props, 'import_compositing')


def draw_assetbar_show_hide(layout, props):
    wm = bpy.context.window_manager
    ui_props = getattr(wm, HANA3D_UI)

    if ui_props.assetbar_on:
        icon = 'HIDE_OFF'
        ttip = 'Click to Hide Asset Bar'
    else:
        icon = 'HIDE_ON'
        ttip = 'Click to Show Asset Bar'
    op = layout.operator(f'view3d.{HANA3D_NAME}_asset_bar', text='', icon=icon)
    op.keep_running = False
    op.do_search = False

    op.tooltip = ttip


class VIEW3D_PT_hana3d_login(Panel):
    bl_category = HANA3D_DESCRIPTION
    bl_idname = f"VIEW3D_PT_{HANA3D_NAME}_login"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f"{HANA3D_DESCRIPTION} Login"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        layout = self.layout
        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

        if user_preferences.login_attempt:
            draw_login_progress(layout)
            return

        draw_login_buttons(layout)


def draw_login_progress(layout):
    layout.label(text='Login through browser')
    layout.label(text='in progress.')
    layout.operator(f"wm.{HANA3D_NAME}_login_cancel", text="Cancel", icon='CANCEL')


def draw_login_buttons(layout):
    user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences

    if user_preferences.login_attempt:
        draw_login_progress(layout)
    else:
        if user_preferences.api_key == '':
            layout.operator(f"wm.{HANA3D_NAME}_login", text="Login / Sign up", icon='URL')
        else:
            layout.operator(f"wm.{HANA3D_NAME}_logout", text="Logout", icon='URL')


class VIEW3D_PT_hana3d_unified(Panel):
    bl_category = HANA3D_DESCRIPTION
    bl_idname = f"VIEW3D_PT_{HANA3D_NAME}_unified"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = f"Find and Upload Assets to {HANA3D_DESCRIPTION}"

    @classmethod
    def poll(cls, context):
        return True

    def draw(self, context):
        s = context.scene
        ui_props = getattr(context.window_manager, HANA3D_UI)
        user_preferences = bpy.context.preferences.addons[HANA3D_NAME].preferences
        layout = self.layout

        row = layout.row()
        row.prop(ui_props, 'down_up', expand=True, icon_only=False)
        layout.prop(ui_props, 'asset_type', expand=False, text='')

        w = context.region.width
        if user_preferences.login_attempt:
            draw_login_progress(layout)
            return

        if len(user_preferences.api_key) < 20 and user_preferences.asset_counter > 20:
            draw_login_buttons(layout)
            layout.separator()

        if ui_props.down_up == 'SEARCH':
            if utils.profile_is_validator():
                search = Search(context)
                search_props = search.props
                layout.prop(search_props, 'search_verification_status')
            if ui_props.asset_type == 'MODEL':
                draw_panel_common_search(self.layout, context)
            elif ui_props.asset_type == 'SCENE':
                draw_panel_common_search(self.layout, context)
            elif ui_props.asset_type == 'MATERIAL':
                draw_panel_common_search(self.layout, context)

        elif ui_props.down_up == 'UPLOAD':
            if not ui_props.assetbar_on:
                text = 'Show asset preview - ;'
            else:
                text = 'Hide asset preview - ;'
            op = layout.operator(f'view3d.{HANA3D_NAME}_asset_bar', text=text, icon='EXPORT')
            op.keep_running = False
            op.do_search = False
            op.tooltip = 'Show/Hide asset preview'

            e = s.render.engine
            if e not in ('CYCLES', 'BLENDER_EEVEE'):
                rtext = (
                    'Only Cycles and EEVEE render engines are currently supported. '
                    f"Please use Cycles for all assets you upload to {HANA3D_DESCRIPTION}."
                )
                label_multiline(layout, rtext, icon='ERROR', width=w)
                return

            if ui_props.asset_type == 'MODEL':
                if bpy.context.view_layer.objects.active is not None:
                    draw_panel_common_upload(self.layout, context)
                else:
                    layout.label(text='selet object to upload')
            elif ui_props.asset_type == 'SCENE':
                draw_panel_common_upload(self.layout, context)
            elif ui_props.asset_type == 'MATERIAL':
                if (
                    bpy.context.view_layer.objects.active is not None
                    and bpy.context.active_object.active_material is not None
                ):
                    draw_panel_common_upload(self.layout, context)
                else:
                    label_multiline(
                        layout,
                        text='select object with material to upload materials',
                        width=w
                    )




def header_search_draw(self, context):
    '''Top bar menu in 3d view'''

    if not utils.guard_from_crash():
        return

    preferences = context.preferences.addons[HANA3D_NAME].preferences
    if preferences.search_in_header:
        layout = self.layout
        ui_props = getattr(context.window_manager, HANA3D_UI)
        search = Search(context)
        search_props = search.props

        if context.space_data.show_region_tool_header is True or context.mode[:4] not in (
            'EDIT',
            'OBJE',
        ):
            layout.separator_spacer()
        layout.prop(ui_props, 'asset_type', text='', icon='URL')
        layout.prop(search_props, 'search_keywords', text='', icon='VIEWZOOM')
        draw_assetbar_show_hide(layout, search_props)



classes = (
    Hana3DUpdaterPanel,
    VIEW3D_PT_hana3d_login,
    VIEW3D_PT_hana3d_unified,
    Hana3DDownloadPanel,
    Hana3DRenderPanel,
)


def register():
    addon_updater_ops.make_annotations(Hana3DUpdaterPanel)
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.VIEW3D_MT_editor_menus.append(header_search_draw)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_editor_menus.remove(header_search_draw)
