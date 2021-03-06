"""Animated mesh Validator."""

import logging
from typing import List, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType


def _check_armature_parent(blend_object: bpy.types.Object) -> bool:
    while blend_object.parent:
        blend_object = blend_object.parent
        if blend_object.type == 'ARMATURE':
            return True
    return False


def _check_animated(blend_object: bpy.types.Object) -> bool:
    if blend_object.type == 'MESH' and blend_object.modifiers:
        for mod in blend_object.modifiers:
            if mod.type == 'ARMATURE':
                return True
    return False


def _get_incorrect_animated_meshes(models: List[str]) -> List[str]:
    meshes = []
    for model in models:
        blend_object = bpy.data.objects[model]
        if _check_armature_parent(blend_object) and not _check_animated(blend_object):
            meshes.append(model)
    return meshes


def _get_object_list(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return export_data.get('models', [])
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return scene.objects.keys()
    return []


def check_animated_meshes(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if animated meshes are parented to ARMATURE object.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running animated meshes check...')
    is_valid = True
    message = 'Asset has no animated meshes wrongly parented.'

    object_list = _get_object_list(asset_type, export_data)
    incorrect_objects = _get_incorrect_animated_meshes(object_list)

    if incorrect_objects:
        message = f'Static meshes parented to armature: {", ".join(incorrect_objects)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Animated meshes check'
description = 'Checks if only animated meshes are parented to armature'
animated_meshes_check = BaseValidator(name, Category.warning, description, check_animated_meshes)
