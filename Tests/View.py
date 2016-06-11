from TM1py import TM1pyQueries as TM1,TM1pyLogin, NativeView, MDXView
import uuid
import unittest
import random

'''
Fails when random_boolean is True - private MDXViews cant be read, updated, deleted (TM1 Bug).
'''

class TestViewMethods(unittest.TestCase):
    login = TM1pyLogin.native('admin', 'apple')
    tm1 = TM1(ip='', port=8001, login=login, ssl=False)
    random_string = str(uuid.uuid4())
    random_boolean = bool(random.getrandbits(1))

    native_view_name = 'TM1py_unittest_native_view_' + random_string
    mdx_view_name = 'TM1py_unittest_mdx_view_' + random_string

    def test1_create_view(self):
        # create instance of native View
        native_view = NativeView(name_cube='Plan_BudgetPlan',
                                 name_view=self.native_view_name)

        # set up native view - put subsets on Rows, Columns and Titles
        subset = self.tm1.get_subset(dimension_name='plan_version', subset_name='FY 2004 Budget')
        native_view.add_row(dimension_name='plan_version', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_business_unit', subset_name='n level business unit')
        native_view.add_row(dimension_name='plan_business_unit', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_department', subset_name='n level departments')
        native_view.add_row(dimension_name='plan_department', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_chart_of_accounts', subset_name='Consolidations')
        native_view.add_row(dimension_name='plan_chart_of_accounts', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_source', subset_name='budget')
        native_view.add_row(dimension_name='plan_source', subset=subset)

        subset = self.tm1.get_subset(dimension_name='plan_exchange_rates', subset_name='actual')
        native_view.add_title(dimension_name='plan_exchange_rates', subset=subset, selection='actual')

        subset = self.tm1.get_subset(dimension_name='plan_time', subset_name='2003 Total Year')
        native_view.add_column(dimension_name='plan_time', subset=subset)

        # create native view on Server
        self.tm1.create_view(view=native_view, private=self.random_boolean)

        # create instance of MDXView
        mdx = "SELECT {([plan_version].[FY 2003 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
              "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
              "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
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

    def test3_update_view(self):
        # get native view
        native_view_original = self.tm1.get_native_view(cube_name='Plan_BudgetPlan',
                                                        view_name=self.native_view_name,
                                                        private=self.random_boolean)
        # modify it
        native_view = self.tm1.get_native_view(cube_name='Plan_BudgetPlan',
                                               view_name=self.native_view_name,
                                               private=self.random_boolean)

        native_view.remove_row(dimension_name='plan_version')
        subset = self.tm1.get_subset(dimension_name='plan_version', subset_name='All Versions')
        native_view.add_column(dimension_name='plan_version',  subset=subset)
        # update it on Server
        self.tm1.update_view(native_view, private=self.random_boolean)
        #get it and check if its different
        native_view_updated = self.tm1.get_native_view(cube_name='Plan_BudgetPlan',
                                                       view_name=self.native_view_name,
                                                       private=self.random_boolean)
        self.assertNotEqual(native_view_original.body, native_view_updated.body)

        # get mdx view
        mdx_view_original = self.tm1.get_mdx_view(cube_name='Plan_BudgetPlan',
                                                  view_name=self.mdx_view_name,
                                                  private=self.random_boolean)
        # modify it
        mdx_view = self.tm1.get_mdx_view(cube_name='Plan_BudgetPlan',
                                         view_name=self.mdx_view_name,
                                         private=self.random_boolean)
        mdx = "SELECT {([plan_version].[FY 2004 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
        "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
        "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
        mdx_view.set_MDX(mdx)
        # update it on Server
        self.tm1.update_view(mdx_view)
        # get it and check if its different
        mdx_view_updated = self.tm1.get_mdx_view(cube_name='Plan_BudgetPlan',
                                                 view_name=self.mdx_view_name,
                                                 private=self.random_boolean)
        self.assertNotEqual(mdx_view_original.body, mdx_view_updated.body)

    def test4_delete_view(self):
        self.tm1.delete_view(cube_name='Plan_BudgetPlan', view_name=self.native_view_name, private=self.random_boolean)
        self.tm1.delete_view(cube_name='Plan_BudgetPlan', view_name=self.mdx_view_name, private=self.random_boolean)

    def test5_logout(self):
        self.tm1.logout()

if __name__ == '__main__':
    unittest.main()
