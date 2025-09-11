import configparser
import time
import unittest
from pathlib import Path

from mdxpy import MdxBuilder, Member

from TM1py.Objects import Sandbox, Cube, Element, Hierarchy, Dimension, Rules
from TM1py.Services import TM1Service


class TestSandboxService(unittest.TestCase):
    tm1: TM1Service

    prefix = "TM1py_Tests_Sandbox_"
    cube_name = prefix + "some_name"
    dimension_names = [prefix + "dimension1", prefix + "dimension2", prefix + "dimension3"]
    sandbox_name1 = prefix + "sandbox1"
    sandbox_name2 = prefix + "sandbox2"
    sandbox_name3 = prefix + "sandbox3"

    def setUp(self):

        # Connection to TM1
        self.config = configparser.ConfigParser()
        self.config.read(Path(__file__).parent.joinpath("config.ini"))
        self.tm1 = TM1Service(**self.config["tm1srv01"])

        for dimension_name in self.dimension_names:
            elements = [Element("Element {}".format(str(j)), "Numeric") for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_name=dimension_name, name=dimension_name, elements=elements)
            dimension = Dimension(dimension_name, [hierarchy])
            if not self.tm1.dimensions.exists(dimension.name):
                self.tm1.dimensions.create(dimension)

        # Build Cube
        cube = Cube(self.cube_name, self.dimension_names)
        if not self.tm1.cubes.exists(self.cube_name):
            self.tm1.cubes.create(cube)
        c = Cube(self.cube_name, dimensions=self.dimension_names, rules=Rules(""))
        if self.tm1.cubes.exists(c.name):
            self.tm1.cubes.delete(c.name)
        self.tm1.cubes.create(c)

        if not self.tm1.sandboxes.exists(self.sandbox_name1):
            self.tm1.sandboxes.create(Sandbox(name=self.sandbox_name1, include_in_sandbox_dimension=True))

    def test_get_sandbox(self):
        sandbox = self.tm1.sandboxes.get(self.sandbox_name1)

        self.assertEqual(self.sandbox_name1, sandbox.name)
        self.assertTrue(sandbox.include_in_sandbox_dimension)
        self.assertTrue(sandbox.loaded)
        self.assertFalse(sandbox.active)
        self.assertFalse(sandbox.queued)

    def test_get_all_names(self):
        sandbox_names = self.tm1.sandboxes.get_all_names()

        self.assertGreater(len(sandbox_names), 0)
        self.assertIn(self.sandbox_name1, sandbox_names)

    def test_get_all(self):
        sandboxes = self.tm1.sandboxes.get_all()

        self.assertGreater(len(sandboxes), 0)

    def test_update_sandbox(self):
        sandbox = self.tm1.sandboxes.get(self.sandbox_name1)
        self.assertEqual(self.sandbox_name1, sandbox.name)
        self.assertTrue(sandbox.include_in_sandbox_dimension)

        sandbox.include_in_sandbox_dimension = False
        self.tm1.sandboxes.update(sandbox)

        sandbox = self.tm1.sandboxes.get(self.sandbox_name1)
        self.assertEqual(self.sandbox_name1, sandbox.name)
        self.assertFalse(sandbox.include_in_sandbox_dimension)

    def test_exists(self):
        exists = self.tm1.sandboxes.exists(self.sandbox_name1)

        self.assertTrue(exists)

    def test_delete_sandbox(self):
        sandbox2 = Sandbox(self.sandbox_name2, True)
        self.tm1.sandboxes.create(sandbox2)

        self.tm1.sandboxes.delete(self.sandbox_name2)

        exists = self.tm1.sandboxes.exists(sandbox2)
        self.assertFalse(exists)

    def test_publish(self):
        mdx = (
            MdxBuilder.from_cube(self.cube_name)
            .add_member_tuple_to_columns(
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[2], "Element1"),
            )
            .to_mdx()
        )

        self.tm1.cells.write_values(
            cube_name=self.cube_name,
            cellset_as_dict={("Element1", "Element1", "Element1"): 1},
            sandbox_name=self.sandbox_name1,
        )

        values = self.tm1.cells.execute_mdx_values(mdx=mdx)
        self.assertEqual(None, values[0])

        self.tm1.sandboxes.publish(self.sandbox_name1)

        values = self.tm1.cells.execute_mdx_values(mdx=mdx)
        self.assertEqual(1, values[0])

    def test_reset(self):
        mdx = (
            MdxBuilder.from_cube(self.cube_name)
            .add_member_tuple_to_columns(
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[2], "Element1"),
            )
            .to_mdx()
        )

        self.tm1.cells.write_values(
            cube_name=self.cube_name,
            cellset_as_dict={("Element1", "Element1", "Element1"): 1},
            sandbox_name=self.sandbox_name1,
        )

        values = self.tm1.cells.execute_mdx_values(mdx=mdx, sandbox_name=self.sandbox_name1)
        self.assertEqual(1, values[0])

        self.tm1.sandboxes.reset(sandbox_name=self.sandbox_name1)

        values = self.tm1.cells.execute_mdx_values(mdx=mdx, sandbox_name=self.sandbox_name1)
        self.assertEqual(None, values[0])

    def test_merge_with_clean_after(self):
        mdx = (
            MdxBuilder.from_cube(self.cube_name)
            .add_member_tuple_to_columns(
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[2], "Element1"),
            )
            .to_mdx()
        )

        sandbox2 = Sandbox(self.sandbox_name2, True)
        self.tm1.sandboxes.create(sandbox2)

        self.tm1.cells.write_values(
            cube_name=self.cube_name,
            cellset_as_dict={("Element1", "Element1", "Element1"): 5},
            sandbox_name=self.sandbox_name2,
        )

        self.tm1.sandboxes.merge(
            source_sandbox_name=self.sandbox_name2, target_sandbox_name=self.sandbox_name1, clean_after=True
        )

        values = self.tm1.cells.execute_mdx_values(mdx=mdx, sandbox_name=self.sandbox_name1)
        self.assertEqual(5, values[0])

        values = self.tm1.cells.execute_mdx_values(mdx=mdx, sandbox_name=self.sandbox_name2)
        self.assertEqual(None, values[0])

    def test_merge_without_clean_after(self):
        mdx = (
            MdxBuilder.from_cube(self.cube_name)
            .add_member_tuple_to_columns(
                Member.of(self.dimension_names[0], "Element1"),
                Member.of(self.dimension_names[1], "Element1"),
                Member.of(self.dimension_names[2], "Element1"),
            )
            .to_mdx()
        )

        sandbox2 = Sandbox(self.sandbox_name2, True)
        self.tm1.sandboxes.create(sandbox2)

        self.tm1.cells.write_values(
            cube_name=self.cube_name,
            cellset_as_dict={("Element1", "Element1", "Element1"): 5},
            sandbox_name=self.sandbox_name2,
        )

        self.tm1.sandboxes.merge(
            source_sandbox_name=self.sandbox_name2, target_sandbox_name=self.sandbox_name1, clean_after=False
        )

        values = self.tm1.cells.execute_mdx_values(mdx=mdx, sandbox_name=self.sandbox_name1)
        self.assertEqual(5, values[0])

        values = self.tm1.cells.execute_mdx_values(mdx=mdx, sandbox_name=self.sandbox_name2)
        self.assertEqual(5, values[0])

    def test_unload_sandbox(self):
        sandbox3 = Sandbox(self.sandbox_name3, True)
        self.tm1.sandboxes.create(sandbox3)
        time.sleep(1)
        self.tm1.sandboxes.unload(sandbox3.name)
        sandbox = self.tm1.sandboxes.get(self.sandbox_name3)
        loaded = sandbox.loaded
        self.assertFalse(loaded)

    def test_load_sandbox(self):
        sandbox3 = Sandbox(self.sandbox_name3, False)
        self.tm1.sandboxes.create(sandbox3)

        self.tm1.sandboxes.load(sandbox3.name)
        loaded = (self.tm1.sandboxes.get(self.sandbox_name3)).loaded
        self.assertTrue(loaded)

    def test_active_queued(self):
        sandbox3 = Sandbox(self.sandbox_name3, True, active=True, queued=True)
        self.tm1.sandboxes.create(sandbox3)

        active = (self.tm1.sandboxes.get(self.sandbox_name3)).active
        self.assertFalse(active)

        queued = (self.tm1.sandboxes.get(self.sandbox_name3)).queued
        self.assertFalse(queued)

    def tearDown(self):
        for sandbox_name in [self.sandbox_name1, self.sandbox_name2, self.sandbox_name3]:
            if self.tm1.sandboxes.exists(sandbox_name):
                self.tm1.sandboxes.delete(sandbox_name)

        self.tm1.cubes.delete(self.cube_name)
        for dimension in self.dimension_names:
            self.tm1.dimensions.delete(dimension)
        self.tm1.logout()


if __name__ == "__main__":
    unittest.main()
