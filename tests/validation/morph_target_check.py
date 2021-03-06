"""Morph target tests."""
import unittest
from os.path import dirname, join

import bpy

from hana3d_dev.src.validators.morph_target_check import morph_target_checker


class TestMorphTarget(unittest.TestCase):  # noqa: D101
    def setUp(self):
        """Load test scene."""
        bpy.ops.wm.open_mainfile(filepath=join(dirname(__file__), '../scenes/morph_target.blend'))

    def test_correct_model(self):
        """Test validation function on correct model."""
        export_data = {
            'models': ['Icosphere'],
            'type': 'MODEL',
        }
        expected_result = (True, 'All meshes have no shape keys.')
        morph_target_checker.run_validation(export_data)
        test_result = morph_target_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_correct_material(self):
        """Test validation function on correct material."""
        export_data = {
            'material': 'Material',
            'type': 'MATERIAL',
        }
        expected_result = (True, 'All meshes have no shape keys.')
        morph_target_checker.run_validation(export_data)
        test_result = morph_target_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_incorrect_model(self):
        """Test validation function on incorrect model."""
        export_data = {
            'models': ['Cube', 'Cone'],
            'type': 'MODEL',
        }
        expected_result = (False, 'Meshes with shape keys: Cube, Cone')
        morph_target_checker.run_validation(export_data)
        test_result = morph_target_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

    def test_scene_and_fix(self):
        """Test validation function on incorrect scene and fix."""
        export_data = {
            'scene': 'Scene',
            'type': 'SCENE',
        }
        expected_result = (False, 'Meshes with shape keys: Cube, Cone')
        morph_target_checker.run_validation(export_data)
        test_result = morph_target_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)

        # Run fix
        expected_result = (True, 'All meshes have no shape keys.')
        morph_target_checker.run_fix(export_data)
        morph_target_checker.run_validation(export_data)
        test_result = morph_target_checker.get_validation_result()
        self.assertTrue(test_result == expected_result)
