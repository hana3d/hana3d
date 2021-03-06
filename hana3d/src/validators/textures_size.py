"""Texture size Validator."""
import logging
import math
from contextlib import suppress
from typing import List, Set, Tuple

import bpy

from . import BaseValidator, Category
from ..asset.asset_type import AssetType

MAX_TEXTURE_SIZE = 2048


def _check_potency_of_two(number: int):
    return ((number & (number - 1) == 0) and number != 0)


def _check_wrong_texture_size(image: bpy.types.Image):
    size = image.size[0]
    if size > MAX_TEXTURE_SIZE or not _check_potency_of_two(size):
        return True
    return False


def _get_large_textures_in_objects(models: List[str]) -> Set[str]:
    textures: Set[str] = set()
    with suppress(AttributeError):
        for model in models:
            for mat_slot in bpy.data.objects[model].material_slots:
                textures = textures.union(_get_large_textures_in_material(mat_slot.material))
    return textures


def _get_large_textures_in_material(material: bpy.types.Material) -> Set[str]:
    textures: Set[str] = set()
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and _check_wrong_texture_size(node.image):
            textures.add(node.image.name)    # noqa: WPS220
    return textures


def _get_incorrect_texture_names(asset_type: AssetType, export_data: dict):
    if asset_type == AssetType.model:
        return _get_large_textures_in_objects(export_data.get('models', []))
    if asset_type == AssetType.scene:
        scene_name = export_data.get('scene')
        scene = bpy.data.scenes[scene_name]
        return _get_large_textures_in_objects(scene.objects.keys())
    if asset_type == AssetType.material:
        material = bpy.data.materials[export_data.get('material')]
        return _get_large_textures_in_material(material)


def fix_textures_size(asset_type: AssetType, export_data: dict):
    """Resize textures to a potency of 2 below or equal to 2048.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    """
    large_textures = _get_incorrect_texture_names(asset_type, export_data)
    for texture_name in large_textures:
        texture = bpy.data.images[texture_name]
        if texture.size[0] != texture.size[1]:
            continue
        new_size = min(2**int(math.log(texture.size[0], 2)), MAX_TEXTURE_SIZE)
        texture.scale(new_size, new_size)


def check_textures_size(asset_type: AssetType, export_data: dict) -> Tuple[bool, str]:
    """Check if textures sizes are potency of 2 and below or equal to 2048.

    Parameters:
        asset_type: type of asset that will be uploaded
        export_data: dict containing objects to be uploaded info

    Returns:
        is_valid, message: if check passed and a report message
    """
    logging.info('Running Texture Size Check...')
    is_valid = True
    message = 'All textures sizes are potency of 2 and below or equal to 2048!'

    large_textures = _get_incorrect_texture_names(asset_type, export_data)
    if large_textures:
        message = f'Textures with wrong size: {", ".join(large_textures)}'
        is_valid = False

    logging.info(message)
    return is_valid, message


name = 'Textures Size'
description = 'Checks if texture size is potency of 2 and <= 2048'
textures_size = BaseValidator(
    name,
    Category.warning,
    description,
    check_textures_size,
    fix_textures_size,
)
