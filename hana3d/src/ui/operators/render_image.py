"""Render image operator."""
import bpy

from ...upload import upload
from ....config import HANA3D_NAME
from ....report_tools import execute_wrapper


class ShowRenderImage(bpy.types.Operator):
    """Show render image."""

    bl_idname = f'{HANA3D_NAME}.show_image'
    bl_label = ''

    index: bpy.props.IntProperty(  # type: ignore
        name='index',
    )

    @execute_wrapper
    def execute(self, context):
        """Execute the operator.

        Parameters:
            context: Blender context

        Returns:
            enum set in {‘RUNNING_MODAL’, ‘CANCELLED’, ‘FINISHED’, ‘PASS_THROUGH’, ‘INTERFACE’}
        """
        asset_props = upload.get_upload_props()
        filepath = asset_props.render_list[self.index]['file_path']

        image = bpy.data.images.load(filepath, check_existing=True)
        image.name = asset_props.render_list[self.index]['name']
        asset_props.render_list[self.index]['name'] = image.name

        bpy.ops.render.view_show('INVOKE_DEFAULT')
        screen = bpy.data.screens['temp']
        space = screen.areas[0].spaces[0]
        space.image = image

        return {'FINISHED'}


classes = (
    ShowRenderImage,
)


def register():
    """Register."""
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    """Unregister."""
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)
