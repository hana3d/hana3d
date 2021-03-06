"""Texture size tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.textures_size import textures_size


class TestTextureSize(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/texture_check.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Cube'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All textures sizes are potency of 2 and below or equal to 2048!')
        textures_size.run_validation(export_data)
        test_result = textures_size.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_material(self):
        """Test validation functions on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'All textures sizes are potency of 2 and below or equal to 2048!')
        textures_size.run_validation(export_data)
        test_result = textures_size.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation functions on model with incorrect texture size."""
        export_data = {
            'models': ['Sphere'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Textures with wrong size: TexturesCom_Grass0197_3_M.jpg')
        textures_size.run_validation(export_data)
        test_result = textures_size.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_scene(self):
        """Test validation functions on scene with incorrect texture size."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        textures_size.run_validation(export_data)
        test_result = textures_size.get_validation_result()
        self.assertFalse(test_result[0])
        self.assertTrue('TexturesCom_Grass0197_3_M.jpg' in test_result[1])
        self.assertTrue('grass06  diffuse 4k.jpg' in test_result[1])

    def test_and_fix_incorrect_material_size(self):
        """Test validation and fix functions on material with incorrect texture size."""
        export_data = {
            'material': 'Material.002',
            'type': 'MATERIAL',
        }
        expected_result = (False, 'Textures with wrong size: grass06  diffuse 4k.jpg')
        textures_size.run_validation(export_data)
        test_result = textures_size.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'All textures sizes are potency of 2 and below or equal to 2048!')
        textures_size.run_fix(export_data)
        test_result = textures_size.get_validation_result()
        self.assertTrue(test_result == expected_result)
