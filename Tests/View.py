from TM1py import TM1pyQueries as TM1,TM1pyLogin, NativeView, MDXView, AnnonymousSubset
import uuid
import unittest
import random
import time

'''
TM1 10.2.2 FP < 6
Fails when random_boolean is True - private MDXViews cant be read, updated, deleted (TM1 Bug).

TM1 10.2.2 FP 6
Fails when random boolean is True. Private NativeViews cant be updated

'''

class TestViewMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)
    random_string = str(uuid.uuid4())
    random_boolean = bool(random.getrandbits(1))

    native_view_name = 'TM1py_unittest_native_view_' + random_string
    mdx_view_name = 'TM1py_unittest_mdx_view_' + random_string

    def test0_get_all_views(self):
        views = self.tm1.get_all_views('Plan_BudgetPlan')
        self.assertGreater(len(views), 0)

    def test1_create_view(self):
        # create instance of native View
        native_view = NativeView(cube_name='Plan_BudgetPlan',
                                 view_name=self.native_view_name)

        # set up native view - put subsets on Rows, Columns and Titles
        subset = self.tm1.get_subset(dimension_name='plan_version', subset_name='FY 2004 Budget', private=False)
        native_view.add_row(dimension_name='plan_version', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_business_unit', subset_name='n level business unit',
                                     private=False)
        native_view.add_row(dimension_name='plan_business_unit', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_department', subset_name='n level departments', private=False)
        native_view.add_row(dimension_name='plan_department', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_chart_of_accounts', subset_name='Consolidations',
                                     private=False)
        native_view.add_row(dimension_name='plan_chart_of_accounts', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_exchange_rates', subset_name='local', private=False)
        native_view.add_title(dimension_name='plan_exchange_rates', subset=subset, selection='local')

        subset = self.tm1.get_subset(dimension_name='plan_time', subset_name='2004 Total Year', private=False)
        native_view.add_column(dimension_name='plan_time', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_source', subset_name='budget', private=False)
        native_view.add_column(dimension_name='plan_source', subset=subset)

        # create native view on Server
        self.tm1.create_view(view=native_view, private=self.random_boolean)

        # create instance of MDXView
        nv_view = self.tm1.get_native_view(cube_name='Plan_BudgetPlan', view_name=self.native_view_name,
                                           private=self.random_boolean)
        mdx = nv_view.as_MDX
        mdx_view = MDXView(cube_name='Plan_BudgetPlan',
                           view_name=self.mdx_view_name,
                           MDX=mdx)
        # create mdx view on Server
        self.tm1.create_view(view=mdx_view, private=self.random_boolean)

    def test2_get_view(self):
        # get native view
        native_view = self.tm1.get_native_view(cube_name='Plan_BudgetPlan',
                                               view_name=self.native_view_name,
                                               private=self.random_boolean)
        # check if instance
        self.assertIsInstance(native_view, NativeView)

        # get mdx view
        mdx_view = self.tm1.get_mdx_view(cube_name='Plan_BudgetPlan',
                                         view_name=self.mdx_view_name,
                                         private=self.random_boolean)
        # check if instance
        self.assertIsInstance(mdx_view, MDXView)

    def test3_compare_data(self):
        data_nv = self.tm1.get_view_content('Plan_BudgetPlan', self.native_view_name, private=self.random_boolean)
        data_mdx = self.tm1.get_view_content('Plan_BudgetPlan', self.mdx_view_name, private=self.random_boolean)

        # Sum up all the values from the views
        sum_nv = sum([value['Value'] for value in data_nv.values() if value['Value']])
        sum_mdx = sum([value['Value'] for value in data_mdx.values() if value['Value']])
        self.assertEqual(sum_nv, sum_mdx)

    # fails sometimes because PrivateMDXViews cant be updated in FP < 5.
    def test4_update_nativeview(self):
        # get native view
        native_view_original = self.tm1.get_native_view(cube_name='Plan_BudgetPlan',
                                                        view_name=self.native_view_name,
                                                        private=self.random_boolean)

        # Sum up all the values from the views
        data_original = self.tm1.get_view_content('Plan_BudgetPlan', self.native_view_name, private=self.random_boolean)
        sum_original = sum([value['Value'] for value in data_original.values() if value['Value']])

        # modify it
        native_view_original.remove_row(dimension_name='plan_department')
        subset = AnnonymousSubset('plan_department', elements=["200", "405"])
        native_view_original.add_column(dimension_name='plan_department',  subset=subset)

        # update it on Server
        self.tm1.update_view(native_view_original, private=self.random_boolean)

        #get it and check if its different
        data_updated = self.tm1.get_view_content('Plan_BudgetPlan', self.native_view_name, private=self.random_boolean)
        sum_updated = sum([value['Value'] for value in data_updated.values() if value['Value']])
        self.assertNotEqual(sum_original, sum_updated)


    def test5_update_mdxview(self):
        # get mdx view
        mdx_view_original = self.tm1.get_mdx_view(cube_name='Plan_BudgetPlan',
                                                  view_name=self.mdx_view_name,
                                                  private=self.random_boolean)

        # get data from original view
        data_mdx_original = self.tm1.get_view_content('Plan_BudgetPlan', mdx_view_original.name,
                                                      private=self.random_boolean)

        mdx = "SELECT {([plan_version].[FY 2004 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
        "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
        "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
        mdx_view_original.MDX = mdx
        # update it on Server
        self.tm1.update_view(mdx_view_original, private=self.random_boolean)
        # get it and check if its different
        mdx_view_updated = self.tm1.get_mdx_view(cube_name='Plan_BudgetPlan',
                                                 view_name=self.mdx_view_name,
                                                 private=self.random_boolean)


        data_mdx_updated = self.tm1.get_view_content('Plan_BudgetPlan', mdx_view_updated.name, private=self.random_boolean)

        # Sum up all the values from the views
        sum_mdx_original = sum([value['Value'] for value in data_mdx_original.values() if value['Value']])
        sum_mdx_updated = sum([value['Value'] for value in data_mdx_updated.values() if value['Value']])
        self.assertNotEqual(sum_mdx_original, sum_mdx_updated)





    def test6_delete_view(self):
        self.tm1.delete_view(cube_name='Plan_BudgetPlan', view_name=self.native_view_name, private=self.random_boolean)
        self.tm1.delete_view(cube_name='Plan_BudgetPlan', view_name=self.mdx_view_name, private=self.random_boolean)





if __name__ == '__main__':
    unittest.main()
