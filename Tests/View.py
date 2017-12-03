import random
import unittest
import uuid

from TM1py.Objects import AnonymousSubset, Subset, Cube, Dimension, Element, Hierarchy, MDXView, NativeView
from TM1py.Services import TM1Service

from .config import test_config


cube_name = 'TM1py_unittest_cube'
dimension_names = ['TM1py_unittest_dimension1',
                   'TM1py_unittest_dimension2',
                   'TM1py_unittest_dimension3']


class TestViewMethods(unittest.TestCase):
    tm1 = TM1Service(**test_config)

    random_string = str(uuid.uuid4())
    # Fails when random boolean is True. Private NativeViews cant be updated with TM1 10.2.2 FP 6
    random_boolean = bool(random.getrandbits(1)) \
        if int(tm1.server.get_product_version().split('.')[2]) > 20602 \
        else False

    native_view_name = 'TM1py_unittest_native_view_' + random_string
    mdx_view_name = 'TM1py_unittest_mdx_view_' + random_string

    # Setup Cubes, Dimensions and Subsets
    @classmethod
    def setup_class(cls):
        # Build Dimensions
        for i in range(3):
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            hierarchy = Hierarchy(dimension_names[i], dimension_names[i], elements)
            dimension = Dimension(dimension_names[i], [hierarchy])
            if not cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.create(dimension)
        # Build Cube
        cube = Cube(cube_name, dimension_names)
        if not cls.tm1.cubes.exists(cube_name):
            cls.tm1.cubes.create(cube)
        # Write data into cube
        cellset = {}
        for i in range(10000):
            element1 = 'Element ' + str(random.randint(1, 1000))
            element2 = 'Element ' + str(random.randint(1, 1000))
            element3 = 'Element ' + str(random.randint(1, 1000))
            cellset[(element1, element2, element3)] = random.randint(1, 1000)
        cls.tm1.data.write_values(cube_name, cellset)

    def test1_create_view(self):
        # create instance of native View
        native_view = NativeView(cube_name=cube_name,
                                 view_name=self.native_view_name)

        # Set up native view - put subsets on Rows, Columns and Titles
        subset = Subset(dimension_name=dimension_names[0], hierarchy_name=dimension_names[0], subset_name=str(uuid.uuid4()),
                        expression='{{[{}].Members}}'.format(dimension_names[0]))
        self.tm1.dimensions.subsets.create(subset, private=False)
        native_view.add_row(dimension_name=dimension_names[0], subset=subset)

        subset = AnonymousSubset(dimension_name=dimension_names[1], hierarchy_name=dimension_names[1],
                                 elements=['element1', 'element123', 'element432'])
        native_view.add_title(dimension_name=dimension_names[1], subset=subset, selection='element123')

        elements = ['Element{}'.format(str(i)) for i in range(1, 201)]
        subset = Subset(dimension_name=dimension_names[2], hierarchy_name=dimension_names[2],
                        subset_name=str(uuid.uuid4()), elements=elements)
        self.tm1.dimensions.subsets.create(subset, private=False)
        native_view.add_column(dimension_name=dimension_names[2], subset=subset)

        # Suppress Null Values
        native_view.suppress_empty_cells = True

        # create native view on Server
        self.tm1.cubes.views.create(view=native_view, private=self.random_boolean)

        # create instance of MDXView
        nv_view = self.tm1.cubes.views.get_native_view(cube_name=cube_name,
                                                       view_name=self.native_view_name,
                                                       private=self.random_boolean)
        mdx = nv_view.MDX
        mdx_view = MDXView(cube_name=cube_name,
                           view_name=self.mdx_view_name,
                           MDX=mdx)
        # create mdx view on Server
        self.tm1.cubes.views.create(view=mdx_view, private=self.random_boolean)

    def test2_get_all_views(self):
        private_views, public_views = self.tm1.cubes.views.get_all(cube_name)
        self.assertGreater(len(public_views), 0)

        private_view_names, public_view_names = self.tm1.cubes.views.get_all_names(cube_name)
        self.assertEqual(len(public_views), len(public_view_names))
        self.assertEqual(len(private_views), len(private_view_names))

    def test3_get_view(self):
        # get native view
        native_view = self.tm1.cubes.views.get_native_view(cube_name=cube_name,
                                                           view_name=self.native_view_name,
                                                           private=self.random_boolean)
        # check if instance
        self.assertIsInstance(native_view, NativeView)

        # get mdx view
        mdx_view = self.tm1.cubes.views.get_mdx_view(cube_name=cube_name,
                                                     view_name=self.mdx_view_name,
                                                     private=self.random_boolean)
        # check if instance
        self.assertIsInstance(mdx_view, MDXView)

    def test4_compare_data(self):
        data_nv = self.tm1.data.get_view_content(cube_name, self.native_view_name, private=self.random_boolean)
        data_mdx = self.tm1.data.get_view_content(cube_name, self.mdx_view_name, private=self.random_boolean)

        # Sum up all the values from the views
        sum_nv = sum([value['Value'] for value in data_nv.values() if value['Value']])
        sum_mdx = sum([value['Value'] for value in data_mdx.values() if value['Value']])
        self.assertEqual(sum_nv, sum_mdx)

    # fails sometimes because PrivateMDXViews cant be updated in FP < 5.
    def test5_update_nativeview(self):
        # get native view
        native_view_original = self.tm1.cubes.views.get_native_view(cube_name=cube_name,
                                                                    view_name=self.native_view_name,
                                                                    private=self.random_boolean)

        # Sum up all the values from the views
        data_original = self.tm1.data.get_view_content(cube_name, self.native_view_name, private=self.random_boolean)
        sum_original = sum([value['Value'] for value in data_original.values() if value['Value']])

        # modify it
        native_view_original.remove_row(dimension_name=dimension_names[0])
        subset = AnonymousSubset(dimension_name=dimension_names[0],
                                 elements=["Element 1", "Element 2", "Element 3", "Element 4", "Element 5"])
        native_view_original.add_column(dimension_name=dimension_names[0], subset=subset)

        # update it on Server
        self.tm1.cubes.views.update(native_view_original, private=self.random_boolean)

        # Get it and check if its different
        data_updated = self.tm1.data.get_view_content(cube_name, self.native_view_name, private=self.random_boolean)
        sum_updated = sum([value['Value'] for value in data_updated.values() if value['Value']])
        self.assertNotEqual(sum_original, sum_updated)

    def test6_update_mdxview(self):
        # Get mdx view
        mdx_view_original = self.tm1.cubes.views.get_mdx_view(cube_name=cube_name,
                                                              view_name=self.mdx_view_name,
                                                              private=self.random_boolean)
        # Get data from mdx view
        data_mdx_original = self.tm1.data.get_view_content(cube_name=cube_name,
                                                           view_name=mdx_view_original.name,
                                                           private=self.random_boolean)
        mdx = "SELECT " \
              "NON EMPTY{{ [{}].Members }} ON 0," \
              "NON EMPTY {{ [{}].Members }} ON 1 " \
              "FROM [{}] " \
              "WHERE ([{}].[Element172])".format(dimension_names[0], dimension_names[1], cube_name, dimension_names[2])
        mdx_view_original.MDX = mdx
        # Update mdx view on Server
        self.tm1.cubes.views.update(mdx_view_original, private=self.random_boolean)
        # Get it and check if its different
        mdx_view_updated = self.tm1.cubes.views.get_mdx_view(cube_name=cube_name,
                                                             view_name=self.mdx_view_name,
                                                             private=self.random_boolean)

        data_mdx_updated = self.tm1.data.get_view_content(cube_name,
                                                          mdx_view_updated.name,
                                                          private=self.random_boolean)

        # Sum up all the values from the views
        sum_mdx_original = sum([value['Value'] for value in data_mdx_original.values() if value['Value']])
        sum_mdx_updated = sum([value['Value'] for value in data_mdx_updated.values() if value['Value']])
        self.assertNotEqual(sum_mdx_original, sum_mdx_updated)

    def test7_delete_view(self):
        self.tm1.cubes.views.delete(cube_name=cube_name, view_name=self.native_view_name, private=self.random_boolean)
        self.tm1.cubes.views.delete(cube_name=cube_name, view_name=self.mdx_view_name, private=self.random_boolean)

    @classmethod
    def teardown_class(cls):
        cls.tm1.cubes.delete(cube_name)
        for dimension_name in dimension_names:
            cls.tm1.dimensions.delete(dimension_name)
        cls.tm1.logout()

    
if __name__ == '__main__':
    unittest.main()
