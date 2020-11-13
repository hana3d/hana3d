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

import copy
import functools
import os
import shutil
import threading
from queue import Queue

import bpy
import requests
from bpy.app.handlers import persistent
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty
)

from . import append_link, colors, paths, render_tools, types, ui, utils
from .report_tools import execute_wrapper
from .config import (
    HANA3D_NAME,
    HANA3D_DESCRIPTION,
    HANA3D_MODELS,
    HANA3D_SCENES,
)

download_threads = {}
append_tasks_queue = Queue()


class ThreadCom:  # object passed to threads to read background process stdout info
    def __init__(self):
        self.file_size = 1000000000000000  # property that gets written to.
        self.downloaded = 0
        self.lasttext = ''
        self.error = False
        self.report = ''
        self.progress = 0.0
        self.passargs = {}


class Downloader(threading.Thread):
    def __init__(self, asset_data: dict, tcom: ThreadCom):
        super(Downloader, self).__init__()
        self.asset_data = asset_data
        self.tcom = tcom
        self._stop_event = threading.Event()
        self._remove_event = threading.Event()
        self._finish_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def mark_remove(self):
        self._remove_event.set()

    @property
    def marked_remove(self):
        return self._remove_event.is_set()

    def finish(self):
        self._finish_event.set()

    @property
    def finished(self):
        return self._finish_event.is_set()

    # def main_download_thread(asset_data, tcom):
    def run(self):
        '''try to download file from hana3d'''
        asset_data = self.asset_data
        tcom = self.tcom

        if tcom.error:
            return
        # only now we can check if the file already exists.
        # This should have 2 levels, for materials
        # different than for the non free content.
        # delete is here when called after failed append tries.
        if check_existing(asset_data) and not tcom.passargs.get('delete'):
            # this sends the thread for processing,
            # where another check should occur,
            # since the file might be corrupted.
            tcom.downloaded = 100
            utils.p('not downloading, trying to append again')
            return

        file_name = paths.get_download_filenames(asset_data)[0]  # prefer global dir if possible.
        # for k in asset_data:
        #    print(asset_data[k])
        if self.stopped():
            utils.p('stopping download: ' + asset_data['name'])
            return

        tmp_file = file_name + '_tmp'
        with open(tmp_file, "wb") as f:
            print("Downloading %s" % file_name)

            response = requests.get(asset_data['download_url'], stream=True)
            total_length = response.headers.get('Content-Length')

            if total_length is None:  # no content length header
                f.write(response.content)
            else:
                tcom.file_size = int(total_length)
                dl = 0
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    tcom.downloaded = dl
                    tcom.progress = int(100 * tcom.downloaded / tcom.file_size)
                    f.write(data)
                    if self.stopped():
                        utils.p('stopping download: ' + asset_data['name'])
                        f.close()
                        os.remove(tmp_file)
                        return
        os.rename(tmp_file, file_name)


def check_missing():
    '''checks for missing files, and possibly starts re-download of these into the scene'''
    # missing libs:
    # TODO: put these into a panel and let the user decide if these should be downloaded.
    missing = []
    for library in bpy.data.libraries:
        fp = library.filepath
        if fp.startswith('//'):
            fp = bpy.path.abspath(fp)
        if not os.path.exists(fp) and library.get('asset_data') is not None:
            missing.append(library)

    for library in missing:
        asset_data = library['asset_data']
        downloaded = check_existing(asset_data)
        if downloaded:
            try:
                library.reload()
            except Exception:
                download(library['asset_data'], redownload=True)
        else:
            download(library['asset_data'], redownload=True)


def check_unused():
    '''find assets that have been deleted from scene but their library is still present.'''

    used_libs = []
    for ob in bpy.data.objects:
        if ob.instance_collection is not None and ob.instance_collection.library is not None:
            # used_libs[ob.instance_collection.name] = True
            if ob.instance_collection.library not in used_libs:
                used_libs.append(ob.instance_collection.library)

        for ps in ob.particle_systems:
            if (
                ps.settings.render_type == 'GROUP'
                and ps.settings.instance_collection is not None
                and ps.settings.instance_collection.library not in used_libs
            ):
                used_libs.append(ps.settings.instance_collection)

    for library in bpy.data.libraries:
        if library not in used_libs:
            print('attempt to remove this library: ', library.filepath)
            # have to unlink all groups, since the file is a 'user'
            # even if the groups aren't used at all...
            for user_id in library.users_id:
                if type(user_id) == bpy.types.Collection:
                    bpy.data.collections.remove(user_id)
            library.user_clear()


@persistent
def scene_save(context):
    ''' does cleanup of Hana3D props and sends a message to the server about assets used.'''
    # TODO this can be optimized by merging these 2 functions, since both iterate over all objects.
    if not bpy.app.background:
        check_unused()


@persistent
def scene_load(context):
    '''restart broken downloads on scene load'''
    global download_threads
    download_threads = {}

    check_missing()


def set_thumbnail(asset_data, asset):
    thumbnail_name = asset_data['thumbnail'].split(os.sep)[-1]
    tempdir = paths.get_temp_dir(f'{asset_data["asset_type"]}_search')
    thumbpath = os.path.join(tempdir, thumbnail_name)
    asset_thumbs_dir = paths.get_download_dirs(asset_data["asset_type"])[0]
    asset_thumb_path = os.path.join(asset_thumbs_dir, thumbnail_name)
    shutil.copy(thumbpath, asset_thumb_path)
    asset_props = getattr(asset, HANA3D_NAME)
    asset_props.thumbnail = asset_thumb_path


def update_downloaded_progress(downloader: Downloader):
    sr = bpy.context.window_manager.get(f'{HANA3D_NAME}_search_results')
    if sr is None:
        utils.p(f'{HANA3D_NAME}_search_results not found')
        return
    for r in sr:
        if r.get('view_id') == downloader.asset_data['view_id']:
            r['downloaded'] = downloader.tcom.progress
            return


def remove_file(filepath):
    try:
        os.remove(filepath)
    except Exception as e:
        utils.p(f'Error when removing {filepath}: {e}')


def process_finished_thread(downloader: Downloader):
    asset_data = downloader.asset_data
    tcom = downloader.tcom

    file_names = paths.get_download_filenames(asset_data)
    # duplicate file if the global and subdir are used in prefs
    # todo this should try to check if both files exist and are ok.
    if len(file_names) == 2:
        shutil.copyfile(file_names[0], file_names[1])

    if tcom.passargs.get('redownload'):
        # handle lost libraries here:
        for library in bpy.data.libraries:
            if (
                library.get('asset_data') is not None
                and library['asset_data']['view_id'] == asset_data['view_id']
            ):
                library.filepath = file_names[-1]
                library.reload()
        return
    append_asset_safe(asset_data, **tcom.passargs)


def cleanup_threads():
    global download_threads
    download_threads = {
        view_id: downloader
        for view_id, downloader in download_threads.items()
        if not downloader.marked_remove
    }


def execute_append_tasks():
    if append_tasks_queue.empty():
        return 0.5
    if any(thread.is_alive() for thread in download_threads.values()):
        return 0.1

    task = append_tasks_queue.get()
    try:
        task()
        append_tasks_queue.task_done()
    except Exception as e:
        asset_data, = task.args
        file_names = file_names = paths.get_download_filenames(asset_data)
        for f in file_names:
            remove_file(f)
        ui.add_report(f'Error when appending {asset_data["name"]} to scene: {e}', color=colors.RED)
    return 0.01


# @bpy.app.handlers.persistent
def timer_update():  # TODO might get moved to handle all hana3d stuff, not to slow down.
    '''check for running and finished downloads and react. write progressbars too.'''
    if len(download_threads) == 0:
        return 1.0
    for view_id, downloader in download_threads.items():
        if downloader.finished:
            # Ignore download theads that are finished but the asset was not appended
            continue
        asset_data = downloader.asset_data
        if downloader.is_alive():
            update_downloaded_progress(downloader)
            continue

        if downloader.tcom.error:
            sprops = utils.get_search_props()
            sprops.report = downloader.tcom.report
            downloader.mark_remove()
            ui.add_report(f'Error when downloading {asset_data["name"]}', color=colors.RED)
            continue

        if bpy.context.mode == 'EDIT' and asset_data['asset_type'] in ('model', 'material'):
            continue

        downloader.tcom.progress = 100
        update_downloaded_progress(downloader)
        process_finished_thread(downloader)
        downloader.finish()

    cleanup_threads()

    return 0.1


def download(asset_data, **kwargs):
    '''start the download thread'''

    tcom = ThreadCom()
    tcom.passargs = kwargs

    # incoming data can be either directly dict from python, or blender id property
    # (recovering failed downloads on reload)
    if type(asset_data) == dict:
        asset_data = copy.deepcopy(asset_data)
    else:
        asset_data = asset_data.to_dict()
    thread = Downloader(asset_data, tcom)
    thread.start()

    view_id = asset_data['view_id']
    download_threads[view_id] = thread


def add_import_params(thread: Downloader, location, rotation):
    params = {
        'location': location,
        'rotation': rotation,
    }
    thread.tcom.passargs['import_params'].append(params)


def check_existing(asset_data):
    ''' check if the object exists on the hard drive'''
    file_names = paths.get_download_filenames(asset_data)

    if len(file_names) == 2:
        # TODO this should check also for failed or running downloads.
        # If download is running, assign just the running thread.
        # if download isn't running but the file is wrong size,
        #  delete file and restart download (or continue downoad? if possible.)
        if os.path.isfile(file_names[0]) and not os.path.isfile(file_names[1]):
            shutil.copy(file_names[0], file_names[1])
        # only in case of changed settings or deleted/moved global dict.
        elif not os.path.isfile(file_names[0]) and os.path.isfile(file_names[1]):
            shutil.copy(file_names[1], file_names[0])

    if len(file_names) == 0 or not os.path.isfile(file_names[0]):
        return False

    newer_asset_in_server = (
        asset_data.get('created') is not None
        and float(asset_data['created']) > float(os.path.getctime(file_names[0]))
    )
    if newer_asset_in_server:
        os.remove(file_names[0])
        return False

    return True


def import_scene(asset_data: dict, file_names: list):
    scene = append_link.append_scene(file_names[0], link=False, fake_user=False)
    scene.name = asset_data['name']
    props = getattr(bpy.context.window_manager, HANA3D_SCENES)
    if props.merge_add == 'ADD':
        for window in bpy.context.window_manager.windows:
            window.scene = bpy.data.scenes[asset_data['name']]
    return scene


def import_model(window_manager, asset_data: dict, file_names: list, **kwargs):
    sprops = getattr(window_manager, HANA3D_MODELS)
    if sprops.append_method == 'LINK_COLLECTION':
        sprops.append_link = 'LINK'
        sprops.import_as = 'GROUP'
    else:
        sprops.append_link = 'APPEND'
        sprops.import_as = 'INDIVIDUAL'

    append_or_link = sprops.append_link
    asset_in_scene = check_asset_in_scene(asset_data)
    link = (asset_in_scene == 'LINK') or (append_or_link == 'LINK')

    if kwargs.get('import_params'):
        for param in kwargs['import_params']:
            if link is True:
                parent, newobs = append_link.link_collection(
                    file_names[-1],
                    location=param['location'],
                    rotation=param['rotation'],
                    link=link,
                    name=asset_data['name'],
                    parent=kwargs.get('parent'),
                )
            else:
                parent, newobs = append_link.append_objects(
                    file_names[-1],
                    location=param['location'],
                    rotation=param['rotation'],
                    link=link,
                    name=asset_data['name'],
                    parent=kwargs.get('parent'),
                )

            if parent.type == 'EMPTY' and link:
                bmin = asset_data['bbox_min']
                bmax = asset_data['bbox_max']
                size_min = min(
                    1.0,
                    (bmax[0] - bmin[0] + bmax[1] - bmin[1] + bmax[2] - bmin[2]) / 3
                )
                parent.empty_display_size = size_min

    elif kwargs.get('model_location') is not None:
        if link is True:
            parent, newobs = append_link.link_collection(
                file_names[-1],
                location=kwargs['model_location'],
                rotation=kwargs['model_rotation'],
                link=link,
                name=asset_data['name'],
                parent=kwargs.get('parent'),
            )
        else:
            parent, newobs = append_link.append_objects(
                file_names[-1],
                location=kwargs['model_location'],
                rotation=kwargs['model_rotation'],
                link=link,
                parent=kwargs.get('parent'),
            )
        if parent.type == 'EMPTY' and link:
            bmin = asset_data['bbox_min']
            bmax = asset_data['bbox_max']
            size_min = min(1.0, (bmax[0] - bmin[0] + bmax[1] - bmin[1] + bmax[2] - bmin[2]) / 3)
            parent.empty_display_size = size_min

    if link:
        group = parent.instance_collection

        lib = group.library
        lib['asset_data'] = asset_data

    utils.fill_object_metadata(parent)
    return parent


def import_material(asset_data: dict, file_names: list, **kwargs):
    for m in bpy.data.materials:
        if getattr(m, HANA3D_NAME).view_id == asset_data['view_id']:
            inscene = True
            material = m
            break
    else:
        inscene = False
    if not inscene:
        material = append_link.append_material(file_names[-1], link=False, fake_user=False)
    target_object = bpy.data.objects[kwargs['target_object']]

    if len(target_object.material_slots) == 0:
        target_object.data.materials.append(material)
    else:
        target_object.material_slots[kwargs['material_target_slot']].material = material
    return material


def set_asset_props(asset, asset_data):
    asset_props = getattr(asset, HANA3D_NAME)
    asset_props.clear_data()
    asset['asset_data'] = asset_data

    set_thumbnail(asset_data, asset)

    asset_props.id = asset_data['id']
    asset_props.view_id = asset_data['view_id']
    asset_props.view_workspace = asset_data['workspace']
    asset_props.name = asset_data['name']
    asset_props.tags = ','.join(asset_data['tags'])
    asset_props.description = asset_data['description']

    jobs = render_tools.get_render_jobs(asset_data['asset_type'], asset_data['view_id'])
    asset_props.render_data['jobs'] = jobs

    if 'tags' in asset_data:
        types.update_tags_list(asset_props, bpy.context)
        for tag in asset_data['tags']:
            asset_props.tags_list[tag].selected = True

    if 'libraries' in asset_data:
        libraries_list = asset_props.libraries_list
        types.update_libraries_list(asset_props, bpy.context)
        for library in asset_data['libraries']:
            libraries_list[library["name"]].selected = True
            if 'metadata' in library and library['metadata'] is not None:
                for view_prop in libraries_list[library["name"]].metadata['view_props']:
                    name = f'{libraries_list[library["name"]].name} {view_prop["name"]}'
                    slug = view_prop['slug']
                    if name not in asset_props.custom_props:
                        asset_props.custom_props_info[name] = {
                            'slug': slug,
                            'library_name': libraries_list[library["name"]].name,
                            'library_id': libraries_list[library["name"]].id_
                        }
                    if (
                        'view_props' in library['metadata']
                        and slug in library['metadata']['view_props']
                    ):
                        asset_props.custom_props[name] = library['metadata']['view_props'][slug]  # noqa E501
                    else:
                        asset_props.custom_props[name] = ''


def append_asset(asset_data: dict, **kwargs):
    asset_name = asset_data['name']
    utils.p(f'appending asset {asset_name}')

    file_names = paths.get_download_filenames(asset_data)
    if len(file_names) == 0 or not os.path.isfile(file_names[-1]):
        raise FileNotFoundError(f'Could not find file for asset {asset_name}')

    kwargs['name'] = asset_data['name']
    wm = bpy.context.window_manager

    if asset_data['asset_type'] == 'scene':
        asset = import_scene(asset_data, file_names)
    if asset_data['asset_type'] == 'model':
        asset = import_model(wm, asset_data, file_names, **kwargs)
    elif asset_data['asset_type'] == 'material':
        asset = import_material(asset_data, file_names, **kwargs)

    wm[f'{HANA3D_NAME}_assets_used'] = wm.get(f'{HANA3D_NAME}_assets_used', {})
    wm[f'{HANA3D_NAME}_assets_used'][asset_data['view_id']] = asset_data.copy()

    set_asset_props(asset, asset_data)
    if asset_data['view_id'] in download_threads:
        download_threads.pop(asset_data['view_id'])

    undo_push_context_op = getattr(bpy.ops.wm, f"{HANA3D_NAME}_undo_push_context")
    undo_push_context_op(message='add %s to scene' % asset_data['name'])


def append_asset_safe(asset_data: dict, **kwargs):
    task = functools.partial(append_asset, asset_data, **kwargs)
    append_tasks_queue.put(task)


def check_asset_in_scene(asset_data):
    '''checks if the asset is already in scene. If yes,
    modifies asset data so the asset can be reached again.'''
    wm = bpy.context.window_manager
    au = wm.get(f'{HANA3D_NAME}_assets_used', {})

    id = asset_data.get('view_id')
    if id in au.keys():
        ad = au[id]
        if ad.get('file_name') is not None:

            asset_data['file_name'] = ad['file_name']
            asset_data['download_url'] = ad['download_url']

            c = bpy.data.collections.get(ad['name'])
            if c is not None:
                if c.users > 0:
                    return 'LINK'
            return 'APPEND'
    return ''


def start_download(asset_data, **kwargs):
    '''
    check if file isn't downloading or doesn't exist, then start new download
    '''
    view_id = asset_data['view_id']
    if view_id in download_threads and download_threads[view_id].is_alive():
        if asset_data['asset_type'] in ('model', 'material'):
            thread = download_threads[view_id]
            add_import_params(thread, kwargs['model_location'], kwargs['model_rotation'])
        return

    fexists = check_existing(asset_data)
    asset_in_scene = check_asset_in_scene(asset_data)

    if fexists and asset_in_scene:
        append_asset_safe(asset_data, **kwargs)
        return

    if asset_data['asset_type'] in ('model', 'material'):
        params = {
            'location': kwargs['model_location'],
            'rotation': kwargs['model_rotation'],
        }
        download(asset_data, import_params=[params], **kwargs)

    elif asset_data['asset_type'] == 'scene':
        download(asset_data, **kwargs)


asset_types = (
    ('MODEL', 'Model', 'set of objects'),
    ('SCENE', 'Scene', 'scene'),
    ('MATERIAL', 'Material', 'any .blend Material'),
    ('ADDON', 'Addon', 'addnon'),
)


class Hana3DKillDownloadOperator(bpy.types.Operator):
    """Kill a download"""

    bl_idname = f"scene.{HANA3D_NAME}_download_kill"
    bl_label = f"{HANA3D_DESCRIPTION} Kill Asset Download"
    bl_options = {'REGISTER', 'INTERNAL'}

    view_id: StringProperty()

    @execute_wrapper
    def execute(self, context):
        thread = download_threads.pop(self.view_id)
        thread.stop()

        tasks = []
        while not append_tasks_queue.empty():
            task = append_tasks_queue.get()
            if task.args[0]['view_id'] == self.view_id:
                del task
                break
            tasks.append(task)
        for task in tasks:
            append_tasks_queue.put(task)
        return {'FINISHED'}


class Hana3DDownloadOperator(bpy.types.Operator):
    """Download and link asset to scene. Only link if asset already available locally."""

    bl_idname = f"scene.{HANA3D_NAME}_download"
    bl_label = f"{HANA3D_DESCRIPTION} Asset Download"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    asset_type: EnumProperty(
        name="Type",
        items=asset_types,
        description="Type of download",
        default="MODEL",
    )
    asset_index: IntProperty(
        name="Asset Index",
        description='asset index in search results',
        default=-1
    )

    target_object: StringProperty(
        name="Target Object",
        description="Material or object target for replacement",
        default=""
    )

    material_target_slot: IntProperty(
        name="Asset Index",
        description='asset index in search results',
        default=0
    )
    model_location: FloatVectorProperty(name='Asset Location', default=(0, 0, 0))
    model_rotation: FloatVectorProperty(name='Asset Rotation', default=(0, 0, 0))

    replace: BoolProperty(
        name='Replace',
        description='replace selection with the asset',
        default=False
    )

    cast_parent: StringProperty(name="Particles Target Object", description="", default="")

    @execute_wrapper
    def execute(self, context):
        wm = context.window_manager
        sr = wm[f'{HANA3D_NAME}_search_results']

        # TODO CHECK ALL OCCURRENCES OF PASSING BLENDER ID PROPS TO THREADS!
        asset_data = sr[self.asset_index].to_dict()
        au = wm.get(f'{HANA3D_NAME}_assets_used')
        if au is None:
            wm[f'{HANA3D_NAME}_assets_used'] = {}

        atype = asset_data['asset_type']
        if (
            bpy.context.mode != 'OBJECT'
            and (atype == 'model' or atype == 'material')
            and bpy.context.view_layer.objects.active is not None
        ):
            bpy.ops.object.mode_set(mode='OBJECT')

        if self.replace:  # cleanup first, assign later.
            obs = utils.get_selected_models()

            for ob in obs:
                kwargs = {
                    'cast_parent': self.cast_parent,
                    'target_object': ob.name,
                    'material_target_slot': ob.active_material_index,
                    'model_location': tuple(ob.matrix_world.translation),
                    'model_rotation': tuple(ob.matrix_world.to_euler()),
                    'replace': False,
                    'parent': ob.parent,
                }
                utils.delete_hierarchy(ob)
                start_download(asset_data, **kwargs)
        else:
            kwargs = {
                'cast_parent': self.cast_parent,
                'target_object': self.target_object,
                'material_target_slot': self.material_target_slot,
                'model_location': tuple(self.model_location),
                'model_rotation': tuple(self.model_rotation),
                'replace': False,
            }

            start_download(asset_data, **kwargs)
        return {'FINISHED'}


class Hana3DBatchDownloadOperator(bpy.types.Operator):
    """Download and link all preview assets to scene."""

    bl_idname = f"scene.{HANA3D_NAME}_batch_download"
    bl_label = f"{HANA3D_DESCRIPTION} Batch Download"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    object_count: IntProperty(
        name="Object Count",
        description='number of objects imported to scene',
        default=0,
        options={'HIDDEN'}
    )

    grid_distance: FloatProperty(
        name="Grid Distance",
        description='distance between objects on the grid',
        default=3
    )

    reset: BoolProperty(
        name="Reset Count",
        description='reset counter and download previews from zero',
        default=False
    )

    batch_size: IntProperty(
        default=20
    )

    def _get_location(self):
        x = y = 0
        dx = 0
        dy = -1
        for i in range(self.object_count):
            if x == y or (x < 0 and x == -y) or (x > 0 and x == 1 - y):
                dx, dy = -dy, dx
            x, y = x + dx, y + dy
        self.object_count += 1
        return (self.grid_distance * x, self.grid_distance * y, 0)

    @classmethod
    def poll(cls, context):
        return len(download_threads) == 0

    @execute_wrapper
    def execute(self, context):
        if self.reset is True:
            self.object_count = 0
        wm = context.window_manager
        if f'{HANA3D_NAME}_search_results' not in wm:
            return {'CANCELLED'}
        sr = wm[f'{HANA3D_NAME}_search_results']

        for index, result in zip(range(self.batch_size), sr[self.object_count:]):
            asset_data = result.to_dict()
            location = self._get_location()
            kwargs = {
                'cast_parent': "",
                'target_object': "",
                'material_target_slot': 0,
                'model_location': tuple(location),
                'model_rotation': tuple((0, 0, 0)),
                'replace': False,
            }

            start_download(asset_data, **kwargs)
        self.reset = False
        return {'FINISHED'}


classes = (
    Hana3DDownloadOperator,
    Hana3DBatchDownloadOperator,
    Hana3DKillDownloadOperator
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.handlers.load_post.append(scene_load)
    bpy.app.handlers.save_pre.append(scene_save)

    bpy.app.timers.register(timer_update)
    bpy.app.timers.register(execute_append_tasks)


def unregister():
    if bpy.app.timers.is_registered(execute_append_tasks):
        bpy.app.timers.unregister(execute_append_tasks)
    if bpy.app.timers.is_registered(timer_update):
        bpy.app.timers.unregister(timer_update)

    bpy.app.handlers.save_pre.remove(scene_save)
    bpy.app.handlers.load_post.remove(scene_load)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
