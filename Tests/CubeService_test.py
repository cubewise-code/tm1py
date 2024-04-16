import base64
import configparser
import unittest
import uuid
from pathlib import Path

from TM1py import Element, Hierarchy, Dimension
from TM1py.Objects import Cube
from TM1py.Objects import Rules
from TM1py.Services import TM1Service
from .Utils import skip_if_insufficient_version, skip_if_deprecated_in_version


class TestCubeService(unittest.TestCase):
    tm1: TM1Service
    prefix = "TM1py_Tests_Cube_"

    cube_name = prefix + "some_name"
    cube_name_to_delete = prefix + "Some_Other_Name"
    control_cube_name = '}' + prefix + 'some_control_cube_name'
    dimension_names = [
        prefix + "dimension1",
        prefix + "dimension2",
        prefix + "dimension3"]

    def setUp(self):

        # Connection to TM1
        self.config = configparser.ConfigParser()
        self.config.read(Path(__file__).parent.joinpath('config.ini'))
        self.tm1 = TM1Service(**self.config['tm1srv04'])

        for dimension_name in self.dimension_names:
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_name=dimension_name,
                                  name=dimension_name,
                                  elements=elements)
            dimension = Dimension(dimension_name, [hierarchy])
            if not self.tm1.dimensions.exists(dimension.name):
                self.tm1.dimensions.create(dimension)

        # Build Cube
        cube = Cube(self.cube_name, self.dimension_names)
        if not self.tm1.cubes.exists(self.cube_name):
            self.tm1.cubes.create(cube)
        c = Cube(self.cube_name, dimensions=self.dimension_names, rules=Rules(''))
        if self.tm1.cubes.exists(c.name):
            self.tm1.cubes.delete(c.name)
        self.tm1.cubes.create(c)

        # Build Control Cube
        control_cube = Cube(self.control_cube_name, self.dimension_names)
        if not self.tm1.cubes.exists(self.control_cube_name):
            self.tm1.cubes.create(control_cube)
        c = Cube(self.control_cube_name, dimensions=self.dimension_names, rules=Rules(''))
        if self.tm1.cubes.exists(c.name):
            self.tm1.cubes.delete(c.name)
        self.tm1.cubes.create(c)

    def test_get_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        self.assertIsInstance(c, Cube)
        self.assertEqual(c.dimensions, self.dimension_names)

        cubes = self.tm1.cubes.get_all()
        control_cubes = self.tm1.cubes.get_control_cubes()
        model_cubes = self.tm1.cubes.get_model_cubes()
        self.assertEqual(len(cubes), len(control_cubes + model_cubes))

    def test_update_cube(self):
        c = self.tm1.cubes.get(self.cube_name)
        c.rules = Rules("SKIPCHECK;\nFEEDERS;")
        self.tm1.cubes.update(c)
        # test if rule was actually updated
        c = self.tm1.cubes.get(self.cube_name)
        self.assertEqual(c.rules.text, "SKIPCHECK;\nFEEDERS;")
        self.assertTrue(c.skipcheck)

    def test_get_control_cubes(self):
        control_cubes = self.tm1.cubes.get_control_cubes()
        self.assertGreater(len(control_cubes), 0)
        for cube in control_cubes:
            self.assertTrue(cube.name.startswith("}"))

    def test_get_model_cubes(self):
        model_cubes = self.tm1.cubes.get_model_cubes()
        self.assertGreater(len(model_cubes), 0)
        for cube in model_cubes:
            self.assertFalse(cube.name.startswith("}"))

    def test_get_dimension_names(self):
        dimension_names = self.tm1.cubes.get_dimension_names(self.cube_name)
        self.assertEqual(dimension_names, self.dimension_names)

    def test_get_random_intersection(self):
        intersection1 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=False)
        intersection2 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=False)
        self.assertNotEqual(intersection1, intersection2)
        intersection1 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=True)
        intersection2 = self.tm1.cubes.get_random_intersection(cube_name=self.cube_name, unique_names=True)
        self.assertNotEqual(intersection1, intersection2)

    def test_exists(self):
        self.assertTrue(self.tm1.cubes.exists(self.cube_name))
        self.assertFalse(self.tm1.cubes.exists(uuid.uuid4()))

    def test_create_delete_cube(self):
        cube_name = self.cube_name_to_delete
        # element with index 0 is Sandboxes
        dimension_names = self.tm1.dimensions.get_all_names()[1:3]
        cube = Cube(cube_name, dimension_names)

        all_cubes_before = self.tm1.cubes.get_all_names()
        self.tm1.cubes.update_or_create(cube)
        all_cubes_after = self.tm1.cubes.get_all_names()
        self.assertEqual(
            len(all_cubes_before) + 1,
            len(all_cubes_after))
        self.assertEqual(
            self.tm1.cubes.get_dimension_names(cube_name),
            dimension_names)

        all_cubes_before = self.tm1.cubes.get_all_names()
        self.tm1.cubes.delete(cube_name)
        all_cubes_after = self.tm1.cubes.get_all_names()
        self.assertEqual(len(all_cubes_before) - 1, len(all_cubes_after))

    def test_get_all_names(self):
        all_cubes_before = self.tm1.cubes.get_all_names()
        cubes_with_rules = self.tm1.cubes.get_all_names_with_rules()
        cubes_without_rules = self.tm1.cubes.get_all_names_without_rules()

        self.assertEqual(len(all_cubes_before), len(cubes_with_rules) + len(cubes_without_rules))

        self.assertNotEqual(len(self.tm1.cubes.get_all_names()),
                            len(self.tm1.cubes.get_all_names(skip_control_cubes=True)))

        cube_name = self.prefix + "Some_Other_Name"
        dimension_names = self.tm1.dimensions.get_all_names()[1:3]
        cube = Cube(cube_name, dimension_names)
        self.tm1.cubes.update_or_create(cube)
        self.assertEqual(len(cubes_without_rules) + 1, len(self.tm1.cubes.get_all_names_without_rules()))
        self.assertEqual(len(cubes_with_rules), len(self.tm1.cubes.get_all_names_with_rules()))

        cube.rules = "SKIPCHECK"
        self.tm1.cubes.update(cube)
        self.assertEqual(len(cubes_with_rules) + 1, len(self.tm1.cubes.get_all_names_with_rules()))
        self.assertEqual(len(cubes_without_rules), len(self.tm1.cubes.get_all_names_without_rules()))

        self.tm1.cubes.delete(cube_name)

        cube = self.tm1.cubes.get(self.control_cube_name)
        cube.rules = "SKIPCHECK"
        self.tm1.cubes.update(cube)
        self.assertNotEqual(self.tm1.cubes.get_all_names_with_rules(),
                            self.tm1.cubes.get_all_names_with_rules(skip_control_cubes=True))
        self.assertNotEqual(self.tm1.cubes.get_all_names_without_rules(),
                            self.tm1.cubes.get_all_names_without_rules(skip_control_cubes=True))

    @skip_if_insufficient_version(version="11.4")
    def test_get_storage_dimension_order(self):
        dimensions = self.tm1.cubes.get_storage_dimension_order(cube_name=self.cube_name)
        self.assertEqual(dimensions, self.dimension_names)

    def test_search_for_dimension_happy_case(self):
        cube_names = self.tm1.cubes.search_for_dimension(self.dimension_names[0])
        self.assertEqual([self.cube_name, self.control_cube_name], cube_names)

    def test_search_for_dimension_no_match(self):
        cube_names = self.tm1.cubes.search_for_dimension("NotADimensionName")
        self.assertEqual([], cube_names)

    def test_search_for_dimension_case_insensitive(self):
        cube_names = self.tm1.cubes.search_for_dimension(self.dimension_names[1].upper())
        self.assertEqual([self.cube_name, self.control_cube_name], cube_names)

    def test_search_for_dimension_space_insensitive(self):
        cube_names = self.tm1.cubes.search_for_dimension(" " + self.dimension_names[2] + " ")
        self.assertEqual([self.cube_name, self.control_cube_name], cube_names)

    def test_search_for_dimension_substring_happy_case(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring=self.dimension_names[0])
        self.assertEqual(
            {self.cube_name: [self.dimension_names[0]], self.control_cube_name: [self.dimension_names[0]]},
            cubes)

    def test_search_for_dimension_substring_case_insensitive(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring=self.dimension_names[1].upper())
        self.assertEqual(
            cubes,
            {self.cube_name: [self.dimension_names[1]], self.control_cube_name: [self.dimension_names[1]]})

    def test_search_for_dimension_substring_space_insensitive(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring=" " + self.dimension_names[2] + " ")
        self.assertEqual(
            cubes,
            {self.cube_name: [self.dimension_names[2]], self.control_cube_name: [self.dimension_names[2]]})

    def test_search_for_dimension_substring_no_match(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring="NotADimensionName")
        self.assertEqual({}, cubes)

    def test_search_for_dimension_substring_skip_control_cubes_true(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring="}cubes", skip_control_cubes=True)
        self.assertEqual({}, cubes)

    @skip_if_deprecated_in_version(version="12")
    def test_search_for_dimension_substring_skip_control_cubes_false_v11(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring="}cubes", skip_control_cubes=False)
        self.assertEqual(cubes['}CubeProperties'], ['}Cubes'])

    @skip_if_insufficient_version(version="12")
    def test_search_for_dimension_substring_skip_control_cubes_false_v12(self):
        cubes = self.tm1.cubes.search_for_dimension_substring(substring="}cubes", skip_control_cubes=False)
        self.assertEqual(cubes['}CubeSecurity'], ['}Cubes'])

    def test_get_number_of_cubes(self):
        number_of_cubes = self.tm1.cubes.get_number_of_cubes()
        self.assertIsInstance(number_of_cubes, int)

    @skip_if_insufficient_version(version="11.4")
    def test_update_storage_dimension_order(self):
        self.tm1.cubes.update_storage_dimension_order(
            cube_name=self.cube_name,
            dimension_names=reversed(self.dimension_names))
        dimensions = self.tm1.cubes.get_storage_dimension_order(self.cube_name)
        self.assertEqual(
            list(reversed(dimensions)),
            self.dimension_names)

    @skip_if_insufficient_version(version="11.6")
    @skip_if_deprecated_in_version(version="12")
    def test_load(self):
        response = self.tm1.cubes.load(cube_name=self.cube_name)
        self.assertTrue(response.ok)

    @skip_if_insufficient_version(version="11.6")
    @skip_if_deprecated_in_version(version="12")
    def test_unload(self):
        response = self.tm1.cubes.unload(cube_name=self.cube_name)
        self.assertTrue(response.ok)

    def test_lock(self):
        response = self.tm1.cubes.lock(cube_name=self.cube_name)
        self.assertTrue(response.ok)

    def test_unlock(self):
        self.tm1.cubes.lock(cube_name=self.cube_name)
        response = self.tm1.cubes.unlock(cube_name=self.cube_name)
        self.assertTrue(response.ok)

    def test_check_rules_without_errors(self):
        errors = self.tm1.cubes.check_rules(cube_name=self.cube_name)
        self.assertEqual(0, len(errors))

    def test_check_rules_with_errors(self):
        cube = self.tm1.cubes.get(cube_name=self.cube_name)
        cube.rules = "SKIPCHECK"
        self.tm1.cubes.update(cube)

        errors = self.tm1.cubes.check_rules(cube_name=self.cube_name)
        self.assertEqual(1, len(errors))

    def test_search_for_rule_substring_no_match(self):
        cubes = self.tm1.cubes.search_for_rule_substring(substring="find_nothing")
        self.assertEqual(0, len(cubes))

    def test_search_for_rule_substring_happy_case(self):
        cube = self.tm1.cubes.get(cube_name=self.cube_name)
        cube.rules = "SKIPCHECK;\n#find_me_comment"
        self.tm1.cubes.update(cube)

        cubes = self.tm1.cubes.search_for_rule_substring(substring="find_me_comment")
        self.assertEqual(self.cube_name, cubes[0].name)

    def test_search_for_rule_substring_skip_control_cubes_false(self):
        cube = self.tm1.cubes.get(self.control_cube_name)
        cube.rules = "SKIPCHECK;\n[]=N:1;\n#find_me_comment\nFEEDERS;"
        self.tm1.cubes.update(cube)

        cubes = self.tm1.cubes.search_for_rule_substring(substring="find_me_comment", skip_control_cubes=False)
        self.assertEqual(self.control_cube_name, cubes[0].name)

    def test_search_for_rule_substring_space_insensitive(self):
        cube = self.tm1.cubes.get(self.cube_name)
        cube.rules = "SKIPCHECK;\n[]=N:2;\n#find_me_comment\nFEEDERS;"
        self.tm1.cubes.update(cube)

        cubes = self.tm1.cubes.search_for_rule_substring(substring="find _me _COMMENT", skip_control_cubes=False)
        self.assertEqual(self.cube_name, cubes[0].name)

    def test_search_for_rule_substring_skip_control_cubes_true(self):
        cube = self.tm1.cubes.get(self.control_cube_name)
        cube.rules = "SKIPCHECK;\n#find_me_comment"
        self.tm1.cubes.update(cube)

        cubes = self.tm1.cubes.search_for_rule_substring(substring="find_control_comment", skip_control_cubes=True)
        self.assertEqual(0, len(cubes))

    def test_get_measure_dimension(self):
        measure_dimension = self.tm1.cubes.get_measure_dimension(self.cube_name)

        self.assertEqual(self.dimension_names[-1], measure_dimension)

    def test_toggle_cube_rule(self):
        uncommented = Rules("#comment1\nFEEDSTRINGS;\nUNDEFVALS;\n#comment2\nSKIPCHECK;\n#comment3\n#comment4\n[" \
                            "]=N:2;\n#find_me_comment\nFEEDERS;\n#comment5\n[]=>DB(some_cube);\n#comment6")
        c = self.tm1.cubes.get(self.cube_name)
        c.rules = uncommented
        self.tm1.cubes.update(c)

        self.assertEqual(self.tm1.cubes.get(c.name).has_rules, True)

        # test disabling
        self.tm1.cubes.disable_cube_rule(c, sections=['FEEDSTRINGS'])
        self.tm1.cubes.enable_cube_rule(c, sections=['FEEDSTRINGS'])
        self.assertEqual(c.rules.text, uncommented.text)

        self.tm1.cubes.disable_cube_rule(c, sections=['UNDEFVALS'])
        self.tm1.cubes.enable_cube_rule(c, sections=['UNDEFVALS'])
        self.assertEqual(c.rules.text, uncommented.text)

        self.tm1.cubes.disable_cube_rule(c, sections=['SKIPCHECK', 'FEEDERS'])
        self.tm1.cubes.enable_cube_rule(c, sections=['SKIPCHECK', 'FEEDERS'])
        self.assertEqual(c.rules.text, uncommented.text)

        self.tm1.cubes.disable_cube_rule(c)
        self.assertEqual(c.rules.text.startswith('# B64 ENCODED RULE='), True)

        cells = {('Element 1', 'Element 1', 'Element 1'): 1}
        self.tm1.cells.write_values(self.cube_name, cells)

        self.tm1.cubes.enable_cube_rule(c)
        self.assertEqual(c.rules.text, uncommented.text)

    def tearDown(self):
        self.tm1.cubes.delete(self.cube_name)
        if self.tm1.cubes.exists(self.cube_name_to_delete):
            self.tm1.cubes.delete(self.cube_name_to_delete)
        for dimension in self.dimension_names:
            self.tm1.dimensions.delete(dimension)
        self.tm1.logout()


if __name__ == '__main__':
    unittest.main()
