from TM1py import TM1Queries, NativeView, MDXView
import uuid
import unittest


class TestViewMethods(unittest.TestCase):
    q = TM1Queries(ip='', port=8008, user='admin', password='apple', ssl=True)
    random_string = str(uuid.uuid4())

    def test1_create_view(self):
        # create instance of native View
        native_view = NativeView(name_cube='Plan_BudgetPlan',name_view='native_view_' + self.random_string)

        # set up native view
        native_view.add_row(dimension_name='plan_version', subset_name='FY 2004 Budget')
        native_view.add_row(dimension_name='plan_business_unit', subset_name='n level business unit')
        native_view.add_row(dimension_name='plan_department', subset_name='n level departments')
        native_view.add_row(dimension_name='plan_chart_of_accounts', subset_name='Consolidations')
        native_view.add_row(dimension_name='plan_source', subset_name='budget')
        native_view.add_title(dimension_name='plan_exchange_rates', subset_name='actual', selection='actual')
        native_view.add_column(dimension_name='plan_time', subset_name='2003 Total Year')

        # create native view on Server
        self.q.create_view(view=native_view)

        # create instance of MDXView
        mdx = "SELECT {([plan_version].[FY 2003 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
              "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
              "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
        mdx_view = MDXView(cube_name='Plan_BudgetPlan', view_name='mdx_view_' + self.random_string, MDX=mdx)

        # create mdx view on Server
        self.q.create_view(view=mdx_view)

    def test2_get_view(self):
        # get native view
        native_view = self.q.get_native_view(cube_name='Plan_BudgetPlan', view_name='native_view_' + self.random_string)

        # get mdx view
        mdx_view = self.q.get_mdx_view(cube_name='Plan_BudgetPlan', view_name='mdx_view_' + self.random_string)

        # check if instance
        self.assertIsInstance(native_view, NativeView)

        # check if instance
        self.assertIsInstance(mdx_view, MDXView)

    def test3_update_view(self):
        # get native view
        native_view_original = self.q.get_native_view(cube_name='Plan_BudgetPlan', view_name='native_view_' + self.random_string)

        # modify it
        native_view = self.q.get_native_view(cube_name='Plan_BudgetPlan', view_name='native_view_' + self.random_string)
        native_view.remove_row(dimension_name='plan_version', subset_name='FY 2004 Budget')
        native_view.add_row(dimension_name='plan_version',  subset_name='All Versions')

        # update it
        self.q.update_view(native_view)

        # get it and check if its different
        native_view_updated = self.q.get_native_view(cube_name='Plan_BudgetPlan', view_name='native_view_' + self.random_string)
        self.assertNotEqual(native_view_original.body, native_view_updated.body)

        # get mdx view
        mdx_view_original = self.q.get_mdx_view(cube_name='Plan_BudgetPlan', view_name='mdx_view_' + self.random_string)

        # update
        mdx_view = self.q.get_mdx_view(cube_name='Plan_BudgetPlan', view_name='mdx_view_' + self.random_string)
        mdx = "SELECT {([plan_version].[FY 2004 Budget], [plan_department].[105], [plan_chart_of_accounts].[61030], " \
        "[plan_exchange_rates].[local], [plan_source].[goal] , [plan_time].[Jan-2004]) } on COLUMNS," \
        "{[plan_business_unit].[10110]} on ROWS FROM [plan_BudgetPlan]"
        mdx_view.set_MDX(mdx)
        self.q.update_view(mdx_view)

        # get it and check if its different
        mdx_view_updated = self.q.get_mdx_view(cube_name='Plan_BudgetPlan', view_name='mdx_view_' + self.random_string)
        self.assertNotEqual(mdx_view_original.body, mdx_view_updated.body)

    def test4_delete_view(self):
        self.q.delete_view('Plan_BudgetPlan', 'native_view_' + self.random_string)
        self.q.delete_view('Plan_BudgetPlan', 'mdx_view_' + self.random_string)

    def test5_logout(self):
        self.q.logout()

if __name__ == '__main__':
    unittest.main()
