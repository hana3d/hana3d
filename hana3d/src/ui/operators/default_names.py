"""Assign default object name as props name and object render job name."""
from typing import Set

import bpy

from .... import utils
from ....config import HANA3D_DESCRIPTION, HANA3D_NAME, HANA3D_UI


class DefaultNamesOperator(bpy.types.Operator):
    """Assign default object name as props name and object render job name."""

    bl_idname = f'view3d.{HANA3D_NAME}_default_name'
    bl_label = f'{HANA3D_DESCRIPTION} Default Name'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:  # noqa: D102, WPS210, E501
        # This is for case of closing the area or changing type:
        ui_props = getattr(context.window_manager, HANA3D_UI)

        if ui_props.turn_off:
            return {'CANCELLED'}

        if event.type not in {'LEFTMOUSE', 'RIGHTMOUSE', 'ENTER'}:
            return {'PASS_THROUGH'}

        asset = utils.get_active_asset()
        if asset is None:
            return {'PASS_THROUGH'}

        props = getattr(asset, HANA3D_NAME)

        self._upload(props, asset)

        self._default_render_name(props, asset)

        return {'PASS_THROUGH'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> Set[str]:  # noqa: D102
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _upload(self, props, asset):
        if props.name == '' and props.name != asset.name:
            props.name = asset.name

    def _default_render_name(self, props, asset):
        if props.render_job_name == '':
            if 'jobs' not in props.render_data:
                previous_names = []
            else:
                previous_names = [job['job_name'] for job in props.render_data['jobs']]
            base_name = props.name or asset.name or 'Render'
            for n in range(1000):  # noqa: WPS111
                new_name = f'{base_name}_{n:03d}'
                if new_name not in previous_names:
                    break
            props.render_job_name = new_name
