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

import math
import os
from typing import Union

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty
)
from bpy.types import PropertyGroup

from . import paths, render, search, utils
from .config import (
    HANA3D_PROFILE,
    HANA3D_NAME,
    HANA3D_MODELS,
    HANA3D_SCENES,
    HANA3D_MATERIALS,
)

thumbnail_angles = (
    ('DEFAULT', 'default', ''),
    ('FRONT', 'front', ''),
    ('SIDE', 'side', ''),
    ('TOP', 'top', ''),
)

thumbnail_snap = (
    ('GROUND', 'ground', ''),
    ('WALL', 'wall', ''),
    ('CEILING', 'ceiling', ''),
    ('FLOAT', 'floating', ''),
)

thumbnail_resolutions = (
    ('256', '256', ''),
    ('512', '512 - minimum for public', ''),
    ('1024', '1024', ''),
    ('2048', '2048', ''),
)


class Hana3DUIProps(PropertyGroup):
    def switch_search_results(self, context):
        wm = context.window_manager
        if self.asset_type == 'MODEL':
            wm['search results'] = wm.get('hana3d model search')
            wm['search results orig'] = wm.get('hana3d model search orig')
        elif self.asset_type == 'SCENE':
            wm['search results'] = wm.get('hana3d scene search')
            wm['search results orig'] = wm.get('hana3d scene search orig')
        elif self.asset_type == 'MATERIAL':
            wm['search results'] = wm.get('hana3d material search')
            wm['search results orig'] = wm.get('hana3d material search orig')
        elif self.asset_type == 'HDR':
            wm['search results'] = wm.get('hana3d hdr search')
            wm['search results orig'] = wm.get('hana3d hdr search orig')
        search.load_previews()

    def switch_active_asset_type(self, context):
        self.asset_type = self.asset_type_render

    def asset_type_callback(self, context):
        if self.down_up == 'SEARCH':
            items = (
                (
                    'MODEL',
                    'Find Models',
                    "Find models in the Hana3D online database",
                    'OBJECT_DATAMODE',
                    0,
                ),
                (
                    'SCENE',
                    'Find Scenes',
                    "Find scenes in the Hana3D online database",
                    'SCENE_DATA',
                    1,
                ),
                (
                    'MATERIAL',
                    'Find Materials',
                    "Find materials in the Hana3D online database",
                    'MATERIAL',
                    2,
                ),
                # ("HDR", "Find HDRs", "Find HDRs in the Hana3D online database", "WORLD_DATA", 3),
            )
        else:
            items = (
                ("MODEL", "Upload Model", "Upload a model to Hana3D", "OBJECT_DATAMODE", 0),
                ("SCENE", "Upload Scene", "Upload a scene to Hana3D", "SCENE_DATA", 1),
                ("MATERIAL", "Upload Material", "Upload a material to Hana3D", "MATERIAL", 2),
                # ("HDR", "Upload HDR", "Upload a HDR to Hana3D", "WORLD_DATA", 3),
            )
        return items

    down_up: EnumProperty(
        name="Download vs Upload",
        items=(
            ('SEARCH', 'Search', 'Activate searching', 'VIEWZOOM', 0),
            ('UPLOAD', 'Upload', 'Activate uploading', 'COPYDOWN', 1),
        ),
        description="hana3d",
        default="SEARCH",
    )
    asset_type: EnumProperty(
        name="Hana3D Active Asset Type",
        items=asset_type_callback,
        description="Activate asset in UI",
        default=None,
        update=switch_search_results,
    )
    asset_type_render: EnumProperty(
        name="Hana3D Active Asset Type",
        items=(
            (
                'MODEL',
                'Render Model',
                'Create render representing a single model',
                'OBJECT_DATAMODE',
                0,
            ),
            ('SCENE', 'Render Scene', 'Create render representing whole scene', 'SCENE_DATA', 1),
        ),
        description="Activate asset in UI",
        update=switch_active_asset_type,
    )
    # these aren't actually used ( by now, seems to better use globals in UI module:
    draw_tooltip: BoolProperty(name="Draw Tooltip", default=False)
    tooltip: StringProperty(name="Tooltip", description="asset preview info", default="")

    ui_scale = 1

    thumb_size_def = 96
    margin_def = 0

    thumb_size: IntProperty(name="Thumbnail Size", default=thumb_size_def, min=-1, max=256)

    margin: IntProperty(name="Margin", default=margin_def, min=-1, max=256)
    highlight_margin: IntProperty(
        name="Highlight Margin",
        default=int(margin_def / 2),
        min=-10,
        max=256
    )

    bar_height: IntProperty(
        name="Bar Height",
        default=thumb_size_def + 2 * margin_def,
        min=-1,
        max=2048
    )
    bar_x_offset: IntProperty(name="Bar X Offset", default=20, min=0, max=5000)
    bar_y_offset: IntProperty(name="Bar Y Offset", default=80, min=0, max=5000)

    bar_x: IntProperty(name="Bar X", default=100, min=0, max=5000)
    bar_y: IntProperty(name="Bar Y", default=100, min=50, max=5000)
    bar_end: IntProperty(name="Bar End", default=100, min=0, max=5000)
    bar_width: IntProperty(name="Bar Width", default=100, min=0, max=5000)

    wcount: IntProperty(name="Width Count", default=10, min=0, max=5000)
    hcount: IntProperty(name="Rows", default=5, min=0, max=5000)

    reports_y: IntProperty(name="Reports Y", default=5, min=0, max=5000)
    reports_x: IntProperty(name="Reports X", default=5, min=0, max=5000)

    assetbar_on: BoolProperty(name="Assetbar On", default=False)
    turn_off: BoolProperty(name="Turn Off", default=False)

    mouse_x: IntProperty(name="Mouse X", default=0)
    mouse_y: IntProperty(name="Mouse Y", default=0)

    active_index: IntProperty(name="Active Index", default=-3)
    scrolloffset: IntProperty(name="Scroll Offset", default=0)
    drawoffset: IntProperty(name="Draw Offset", default=0)

    dragging: BoolProperty(name="Dragging", default=False)
    drag_init: BoolProperty(name="Drag Initialisation", default=False)
    drag_length: IntProperty(name="Drag length", default=0)
    draw_drag_image: BoolProperty(name="Draw Drag Image", default=False)
    draw_snapped_bounds: BoolProperty(name="Draw Snapped Bounds", default=False)

    snapped_location: FloatVectorProperty(name="Snapped Location", default=(0, 0, 0))
    snapped_bbox_min: FloatVectorProperty(name="Snapped Bbox Min", default=(0, 0, 0))
    snapped_bbox_max: FloatVectorProperty(name="Snapped Bbox Max", default=(0, 0, 0))
    snapped_normal: FloatVectorProperty(name="Snapped Normal", default=(0, 0, 0))

    snapped_rotation: FloatVectorProperty(
        name="Snapped Rotation",
        default=(0, 0, 0),
        subtype='QUATERNION'
    )

    has_hit: BoolProperty(name="has_hit", default=False)
    thumbnail_image = StringProperty(
        name="Thumbnail Image",
        description="",
        default=paths.get_addon_thumbnail_path('thumbnail_notready.png'),
    )


class Hana3DRenderProps(PropertyGroup):
    def get_render_asset_name(self) -> str:
        props = utils.get_upload_props()
        if props is not None:
            return props.name
        return ''

    def get_balance(self) -> str:
        profile = bpy.context.window_manager.get(HANA3D_PROFILE)
        if not profile:
            return 'N/A'
        balance = profile['user'].get('nrf_balance')
        if balance is None:
            return 'N/A'
        return f'${balance:.2f}'

    def update_cameras(self, context):
        if self.cameras in ('ALL_CAMERAS', 'VISIBLE_CAMERAS'):
            self.frame_animation = 'FRAME'

    render_ui_mode: EnumProperty(
        name='Render UI mode',
        items=(
            ('GENERATE', 'Generate', 'Generate new render', 'SCENE', 0),
            ('UPLOAD', 'Upload', 'Upload render from computer', 'EXPORT', 1),
        ),
    )
    balance: StringProperty(
        name="Balance",
        description="",
        default='N/A',
        get=get_balance,
    )
    asset: StringProperty(name="Asset", description="", get=get_render_asset_name)
    engine: EnumProperty(
        name="Engine",
        items=(
             ("CYCLES", "Cycles", ""),
             ("BLENDER_EEVEE", "Eevee", "")
        ),
        description="",
        get=lambda self: 0  # TODO: Remove getter when both available at notRenderFarm
    )
    frame_animation: EnumProperty(
        name="Frame vs Animation",
        items=(
            ("FRAME", "Single Frame", "Render a single frame", "RENDER_STILL", 0),
            ("ANIMATION", "Animation", "Render a range of frames", "RENDER_ANIMATION", 1),
        ),
        description="",
    )
    cameras: EnumProperty(
        name="Cameras",
        items=(
            ("ACTIVE_CAMERA", "Active camera", "Render with only the active camera"),
            ("VISIBLE_CAMERAS", "Visible cameras", "Render with visible cameras"),
            ("ALL_CAMERAS", "All cameras", "Render with all cameras"),
        ),
        description="",
        update=update_cameras,
    )


def workspace_items(self, context):
    profile = bpy.context.window_manager.get(HANA3D_PROFILE)
    if profile is not None:
        user = profile.get('user')
        if user is not None:
            workspaces = tuple(
                (workspace['id'], workspace['name'], '',) for workspace in user['workspaces']
            )
            return workspaces
    return ()


def search_update(self, context):
    utils.p('search updater')
    # if self.search_keywords != '':
    ui_props = bpy.context.window_manager.Hana3DUI
    if ui_props.down_up != 'SEARCH':
        ui_props.down_up = 'SEARCH'
    search.search()


def update_tags_list(props, context):
    props.tags_list.clear()
    current_workspace = props.workspace
    for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for tag in workspace['tags']:
                new_tag = props.tags_list.add()
                new_tag['name'] = tag


def update_libraries_list(props, context):
    props.libraries_list.clear()
    current_workspace = props.workspace
    for workspace in context.window_manager[HANA3D_PROFILE]['user']['workspaces']:
        if current_workspace == workspace['id']:
            for library in workspace['libraries']:
                new_library = props.libraries_list.add()
                new_library['name'] = library['name']
                new_library.id_ = library['id']
                if library['metadata'] is not None:
                    new_library.metadata['library_props'] = library['metadata']['library_props']
                    new_library.metadata['view_props'] = library['metadata']['view_props']


class Hana3DTagItem(PropertyGroup):
    name: StringProperty(name="Tag Name", default="Unknown")
    selected: BoolProperty(name="Tag Selected", default=False)


class Hana3DLibraryItem(PropertyGroup):
    id_: StringProperty(name="Library ID", default="Unknown")
    name: StringProperty(name="Library Name", default="Unknown")
    selected: BoolProperty(name="Library Selected", default=False)
    metadata: PointerProperty(type=PropertyGroup)


class Hana3DCommonSearchProps:
    def on_workspace_update(self, context):
        update_libraries_list(self, context)
        update_tags_list(self, context)

    def update_tags_input(self, context):
        if self.tags_input != '':
            self.tags_list[self.tags_input].selected = True
            search.search()

    def update_libraries_input(self, context):
        if self.libraries_input != '':
            self.libraries_list[self.libraries_input].selected = True
            search.search()

    # STATES
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search_update,
    )
    is_searching: BoolProperty(
        name="Searching",
        description="search is currently running (internal)",
        default=False
    )
    is_downloading: BoolProperty(
        name="Downloading",
        description="download is currently running (internal)",
        default=False
    )
    search_done: BoolProperty(
        name="Search Completed",
        description="at least one search did run (internal)",
        default=False
    )
    public_only: BoolProperty(
        name="Public assets",
        description="Search only for public assets",
        default=False,
        update=search_update,
    )
    search_error: BoolProperty(
        name="Search Error",
        description="last search had an error",
        default=False
    )
    report: StringProperty(name="Report", description="errors and messages", default="")

    search_verification_status: EnumProperty(
        name="Verification status",
        description="Search by verification status",
        items=(
            ('ALL', 'All', 'All'),
            ('UPLOADING', 'Uploading', 'Uploading'),
            ('UPLOADED', 'Uploaded', 'Uploaded'),
            ('READY', 'Ready for V.', 'Ready for validation (deprecated since 2.8)'),
            ('VALIDATED', 'Validated', 'Calidated'),
            ('ON_HOLD', 'On Hold', 'On Hold'),
            ('REJECTED', 'Rejected', 'Rejected'),
            ('DELETED', 'Deleted', 'Deleted'),
        ),
        default='ALL',
    )

    workspace: EnumProperty(
        items=workspace_items,
        name='User workspaces',
        description='User option to choose between workspaces',
        options={'ANIMATABLE'},
        update=on_workspace_update
    )

    tags_list: CollectionProperty(type=Hana3DTagItem)

    tags_input: StringProperty(
        name="Tags", description="Asset Tags", default="", update=update_tags_input)

    libraries_list: CollectionProperty(type=Hana3DLibraryItem)

    libraries_input: StringProperty(
        name="Libraries",
        description="Libraries to search",
        default="",
        update=update_libraries_input
    )


class Hana3DCommonUploadProps:
    def get_render_job_outputs(self, context):
        preview_collection = render.render_previews[self.view_id]
        if not hasattr(preview_collection, 'previews'):
            preview_collection.previews = []

        n_render_jobs = len(self.render_data['jobs']) if 'jobs' in self.render_data else 0
        if len(preview_collection.previews) != n_render_jobs:
            # Sort jobs to avoid error when appending newer render jobs
            sorted_jobs = sorted(self.render_data['jobs'], key=lambda x: x['created'])
            available_previews = []
            for n, job in enumerate(sorted_jobs):
                job_id = job['id']
                if job_id not in preview_collection:
                    file_path = job['file_path']
                    if not os.path.exists(file_path):
                        continue
                    preview_img = preview_collection.load(job_id, file_path, 'IMAGE')
                else:
                    preview_img = preview_collection[job_id]

                enum_item = (job_id, job['job_name'] or '', '', preview_img.icon_id, n)
                available_previews.append(enum_item)
            preview_collection.previews = available_previews

        return preview_collection.previews

    def get_active_image(self, context):
        preview_collection = render.render_previews['active_images']
        if not hasattr(preview_collection, 'previews'):
            preview_collection.previews = []

        active_images = [
            img
            for img in context.blend_data.images
            if img.get('active') or img.has_data and img.users > 0
        ]
        if len(preview_collection.previews) != len(active_images):
            available_previews = []
            for n, img in enumerate(active_images):
                if img.name not in preview_collection:
                    if img.filepath == '':
                        preview_img = img.preview
                    else:
                        preview_img = preview_collection.load(img.name, img.filepath, 'IMAGE')
                else:
                    preview_img = preview_collection[img.name]

                enum_item = (img.name, img.name or '', '', preview_img.icon_id, n)
                available_previews.append(enum_item)
            preview_collection.previews = available_previews

        return preview_collection.previews

    def on_workspace_update(self, context):
        update_libraries_list(self, context)
        update_tags_list(self, context)

    def update_tags_input(self, context):
        if self.tags_input != '':
            self.tags_list[self.tags_input].selected = True

    def update_libraries_input(self, context):
        if self.libraries_input == '':
            return

        self.libraries_list[self.libraries_input].selected = True
        for view_prop in self.libraries_list[self.libraries_input].metadata['view_props']:
            name = f'{self.libraries_list[self.libraries_input].name} {view_prop["name"]}'
            if name not in self.custom_props:
                self.custom_props_info[name] = {
                    'slug': view_prop['slug'],
                    'library_name': self.libraries_list[self.libraries_input].name,
                    'library_id': self.libraries_list[self.libraries_input].id_
                }
                self.custom_props[name] = ''

    def update_preview(self, context=None):
        """Mark upload preview to be updated by draw calllback"""
        if self.remote_thumbnail:
            self.force_preview_reload = True
        self.has_thumbnail = self.thumbnail != ''

    def clear_data(self):
        """Set all properties to their default values"""
        for cls in self.__class__.mro():
            if not hasattr(cls, '__annotations__'):
                continue
            for attr, (type_, kwargs) in cls.__annotations__.items():
                if 'default' in kwargs:
                    setattr(self, attr, kwargs['default'])

    id: StringProperty(
        name="Asset Id",
        description="ID of the asset (hidden)",
        default=""
    )

    view_id: StringProperty(
        name="View Id",
        description="Unique ID of asset's current revision (hidden)",
        default="",
    )

    view_workspace: StringProperty(
        name="View Workspace",
        description="Unique ID of view's Workspace",
        default="",
    )

    name: StringProperty(
        name="Name",
        description="Main name of the asset",
        default="",
    )

    # this is to store name for purpose of checking if name has changed.
    name_old: StringProperty(
        name="Old Name",
        description="Old name of the asset",
        default="",
    )

    description: StringProperty(
        name="Description",
        description="Description of the asset",
        default=""
    )

    name_changed: BoolProperty(
        name="Name Changed",
        description="Name has changed, the asset has to be re-uploaded with all data",
        default=False,
    )

    is_public: BoolProperty(
        name="Public asset",
        description="Upload asset as public",
        default=False
    )

    uploading: BoolProperty(
        name="Uploading",
        description="True when background process is running",
        default=False,
    )

    upload_state: StringProperty(
        name="State Of Upload",
        description="bg process reports for upload",
        default=''
    )

    thumbnail: StringProperty(
        name="Thumbnail",
        description="Path to the thumbnail - 512x512 .jpg image",
        subtype='FILE_PATH',
        default="",
        update=update_preview,
    )

    force_preview_reload: BoolProperty(
        description="True if upload preview image should be updated",
        default=True,
    )

    is_generating_thumbnail: BoolProperty(
        name="Generating Thumbnail",
        description="True when background process is running",
        default=False,
        update=update_preview,
    )

    remote_thumbnail: BoolProperty(
        name="Generating thumbnail on notrenderfarm",
        default=False,
        update=update_preview,
    )

    has_thumbnail: BoolProperty(
        name="Has Thumbnail",
        description="True when thumbnail was checked and loaded",
        default=False,
    )

    thumbnail_generating_state: StringProperty(
        name="Thumbnail Generating State",
        description="bg process reports for thumbnail generation",
        default='',
    )

    report: StringProperty(
        name="Missing Upload Properties",
        description="used to write down what's missing",
        default='',
    )

    workspace: EnumProperty(
        items=workspace_items,
        name='User workspaces',
        description='User option to choose between workspaces',
        options={'ANIMATABLE'},
        update=on_workspace_update
    )

    publish_message: StringProperty(
        name="Publish Message",
        description="Changes from previous version",
        default=""
    )

    rendering: BoolProperty(
        name="Rendering",
        description="True when object is being rendered in background",
        default=False
    )

    render_state: StringProperty(
        name="Render Generating State",
        default="",
    )

    upload_render_state: StringProperty(
        name="Render Upload State",
        default="",
    )

    uploading_render: BoolProperty(
        name="Uploading Render",
        default=False,
    )

    render_data: PointerProperty(
        type=PropertyGroup,
        description='Container for holding data of completed render jobs',
    )

    render_job_output: EnumProperty(
        name="Previous renders",
        description='Render name',
        items=get_render_job_outputs,
    )

    active_image: EnumProperty(
        name="Local Images",
        description='Images in .blend file',
        items=get_active_image,
    )

    render_job_name: StringProperty(
        name="Name",
        description="Name of render job",
        default=""
    )

    tags_list: CollectionProperty(type=Hana3DTagItem)

    tags_input: StringProperty(
        name="Tags", description="Asset Tags", default="", update=update_tags_input)

    libraries_list: CollectionProperty(type=Hana3DLibraryItem)

    libraries_input: StringProperty(
        name="Libraries",
        description="Upload to libraries",
        default="",
        update=update_libraries_input
    )

    custom_props: PointerProperty(
        type=PropertyGroup
    )

    custom_props_info: PointerProperty(
        type=PropertyGroup
    )


class Hana3DMaterialSearchProps(PropertyGroup, Hana3DCommonSearchProps):
    automap: BoolProperty(
        name="Auto-Map",
        description="reset object texture space and also add automatically a cube mapped UV "
        "to the object. \n this allows most materials to apply instantly to any mesh",
        default=False,
    )


class Hana3DMaterialUploadProps(PropertyGroup, Hana3DCommonUploadProps):
    # TODO remove when removing addon thumbnailer
    texture_size_meters: FloatProperty(
        name="Texture Size in Meters",
        description="face count, autofilled",
        default=1.0,
        min=0
    )

    thumbnail_scale: FloatProperty(
        name="Thumbnail Object Size",
        description="size of material preview object in meters "
        "- change for materials that look better at sizes different than 1m",
        default=1,
        min=0.00001,
        max=10,
    )
    thumbnail_background: BoolProperty(
        name="Thumbnail Background (for Glass only)",
        description="For refractive materials, you might need a background. "
        "Don't use if thumbnail looks good without it!",
        default=False,
    )
    thumbnail_background_lightness: FloatProperty(
        name="Thumbnail Background Lightness",
        description="set to make your material stand out",
        default=0.9,
        min=0.00001,
        max=1,
    )
    thumbnail_samples: IntProperty(
        name="Cycles Samples",
        description="cycles samples setting",
        default=150,
        min=5,
        max=5000
    )
    thumbnail_denoising: BoolProperty(
        name="Use Denoising",
        description="Use denoising",
        default=True
    )
    adaptive_subdivision: BoolProperty(
        name="Adaptive Subdivide",
        description="Use adaptive displacement subdivision",
        default=False,
    )

    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=thumbnail_resolutions,
        description="Thumbnail resolution.",
        default="512",
    )

    thumbnail_generator_type: EnumProperty(
        name="Thumbnail Style",
        items=(
            ('BALL', 'Ball', ""),
            ('CUBE', 'Cube', 'cube'),
            ('FLUID', 'Fluid', 'Fluid'),
            ('CLOTH', 'Cloth', 'Cloth'),
            ('HAIR', 'Hair', 'Hair  '),
        ),
        description="Style of asset",
        default="BALL",
    )

    asset_type: StringProperty(default='MATERIAL')


class Hana3DModelUploadProps(PropertyGroup, Hana3DCommonUploadProps):
    thumbnail_background_lightness: FloatProperty(
        name="Thumbnail Background Lightness",
        description="set to make your material stand out",
        default=0.9,
        min=0.01,
        max=10,
    )

    thumbnail_angle: EnumProperty(
        name='Thumbnail Angle',
        items=thumbnail_angles,
        default='DEFAULT',
        description='thumbnailer angle',
    )

    thumbnail_snap_to: EnumProperty(
        name='Model Snaps To:',
        items=thumbnail_snap,
        default='GROUND',
        description='typical placing of the interior.'
        'Leave on ground for most objects that respect gravity :)',
    )

    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=thumbnail_resolutions,
        description="Thumbnail resolution.",
        default="512",
    )

    thumbnail_samples: IntProperty(
        name="Cycles Samples",
        description="cycles samples setting",
        default=200,
        min=5,
        max=5000
    )
    thumbnail_denoising: BoolProperty(
        name="Use Denoising",
        description="Use denoising",
        default=True
    )

    dimensions: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0, 0, 0),
    )
    bbox_min: FloatVectorProperty(
        name="Bbox Min",
        description="dimensions of the whole asset hierarchy",
        default=(-0.25, -0.25, 0),
    )
    bbox_max: FloatVectorProperty(
        name="Bbox Max",
        description="dimensions of the whole asset hierarchy",
        default=(0.25, 0.25, 0.5),
    )

    face_count: IntProperty(name="Face count", description="face count, autofilled", default=0)
    face_count_render: IntProperty(
        name="Render Face Count",
        description="render face count, autofilled",
        default=0
    )

    object_count: IntProperty(
        name="Number of Objects",
        description="how many objects are in the asset, autofilled",
        default=0,
    )

    has_autotags: BoolProperty(
        name="Has Autotagging Done",
        description="True when autotagging done",
        default=False
    )

    asset_type: StringProperty(default='MODEL')


class Hana3DSceneUploadProps(PropertyGroup, Hana3DCommonUploadProps):
    dimensions: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0, 0, 0),
    )
    bbox_min: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(-0.25, -0.25, 0),
    )
    bbox_max: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0.25, 0.25, 0.5),
    )

    face_count: IntProperty(name="Face Count", description="face count, autofilled", default=0)
    face_count_render: IntProperty(
        name="Render Face Count",
        description="render face count, autofilled",
        default=0
    )

    object_count: IntProperty(
        name="Number of Objects",
        description="how many objects are in the asset, autofilled",
        default=0,
    )

    has_autotags: BoolProperty(
        name="Has Autotagging Done",
        description="True when autotagging done",
        default=False
    )

    thumbnail_denoising: BoolProperty(
        name="Use Denoising",
        description="Use denoising",
        default=True
    )
    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=thumbnail_resolutions,
        description="Thumbnail resolution.",
        default="512",
    )
    thumbnail_samples: IntProperty(
        name="Cycles Samples",
        description="cycles samples setting",
        default=200,
        min=5,
        max=5000
    )
    asset_type: StringProperty(default='SCENE')


class Hana3DModelSearchProps(PropertyGroup, Hana3DCommonSearchProps):
    append_method: EnumProperty(
        name="Import Method",
        items=(
            ('LINK_COLLECTION', 'Link', 'Link Collection'),
            ('APPEND_OBJECTS', 'Append', 'Append as Objects'),
        ),
        description="Appended objects are editable in your scene."
        "Linked assets are saved in original files, "
        "aren't editable but also don't increase your file size",
        default="APPEND_OBJECTS",
    )
    append_link: EnumProperty(
        name="How to Attach",
        items=(('LINK', 'Link', ''), ('APPEND', 'Append', ''),),
        description="choose if the assets will be linked or appended",
        default="APPEND",
    )
    import_as: EnumProperty(
        name="Import as",
        items=(('GROUP', 'group', ''), ('INDIVIDUAL', 'objects', ''),),
        description="choose if the assets will be linked or appended",
        default="GROUP",
    )
    offset_rotation_amount: FloatProperty(
        name="Offset Rotation",
        description="offset rotation, hidden prop",
        default=0,
        min=0,
        max=360,
        subtype='ANGLE',
    )
    offset_rotation_step: FloatProperty(
        name="Offset Rotation Step",
        description="offset rotation, hidden prop",
        default=math.pi / 2,
        min=0,
        max=180,
        subtype='ANGLE',
    )


class Hana3DSceneSearchProps(PropertyGroup, Hana3DCommonSearchProps):
    merge_add: EnumProperty(
        name="How to Attach Scene",
        items=(('MERGE', 'Merge Scenes', ''), ('ADD', 'Add New Scene', ''),),
        description="choose if the scene will be merged or appended",
        default="ADD",
    )
    import_world: BoolProperty(
        name='Import World',
        description="import world data to current scene",
        default=True
    )
    import_render: BoolProperty(
        name='Import Render Settings',
        description="import render settings to current scene",
        default=True,
    )
    import_compositing: BoolProperty(
        name="Import Compositing",
        description="Import compositing nodes",
        default=True,
    )


Props = Union[Hana3DModelUploadProps, Hana3DSceneUploadProps, Hana3DMaterialUploadProps]


classes = (
    Hana3DTagItem,
    Hana3DLibraryItem,
    Hana3DUIProps,
    Hana3DRenderProps,
    Hana3DModelSearchProps,
    Hana3DModelUploadProps,
    Hana3DSceneSearchProps,
    Hana3DSceneUploadProps,
    Hana3DMaterialUploadProps,
    Hana3DMaterialSearchProps
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.Hana3DUI = PointerProperty(type=Hana3DUIProps)
    bpy.types.WindowManager.Hana3DRender = PointerProperty(type=Hana3DRenderProps)

    # MODELS
    setattr(bpy.types.WindowManager, HANA3D_MODELS, PointerProperty(type=Hana3DModelSearchProps))
    setattr(bpy.types.Object, HANA3D_NAME, PointerProperty(type=Hana3DModelUploadProps))

    # SCENES
    setattr(bpy.types.WindowManager, HANA3D_SCENES, PointerProperty(type=Hana3DSceneSearchProps))
    setattr(bpy.types.Scene, HANA3D_NAME, PointerProperty(type=Hana3DSceneUploadProps))

    # MATERIALS
    setattr(bpy.types.WindowManager, HANA3D_MATERIALS, PointerProperty(type=Hana3DMaterialSearchProps))  # noqa E501
    setattr(bpy.types.Material, HANA3D_NAME, PointerProperty(type=Hana3DMaterialUploadProps))


def unregister():
    delattr(bpy.types.Material, HANA3D_NAME)
    delattr(bpy.types.WindowManager, HANA3D_MATERIALS)

    delattr(bpy.types.Scene, HANA3D_NAME)
    delattr(bpy.types.WindowManager, HANA3D_SCENES)

    delattr(bpy.types.Object, HANA3D_NAME)
    delattr(bpy.types.WindowManager, HANA3D_MODELS)

    delattr(bpy.types.WindowManager, 'Hana3DRender')
    delattr(bpy.types.WindowManager, 'Hana3DUI')

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
