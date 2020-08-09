import configparser
import random
import unittest
from pathlib import Path

from _datetime import datetime

from TM1py import TM1Service, Element, ElementAttribute, Hierarchy, Dimension, Cube, NativeView, AnonymousSubset, \
    Subset, Process, Chore, ChoreStartTime, ChoreFrequency, ChoreTask
from TM1py.Objects.Application import CubeApplication, ApplicationTypes, ChoreApplication, DimensionApplication, \
    FolderApplication, LinkApplication, ProcessApplication, SubsetApplication, ViewApplication, DocumentApplication

# Hard coded stuff
PREFIX = 'TM1py_Tests_Applications_'
TM1PY_APP_FOLDER = PREFIX + "RootFolder"
APPLICATION_NAME = PREFIX + "Application"
CUBE_NAME = PREFIX + "Cube"
VIEW_NAME = PREFIX + "View"
SUBSET_NAME = PREFIX + "Subset"
PROCESS_NAME = PREFIX + "Process"
CHORE_NAME = PREFIX + "Chore"
FOLDER_NAME = PREFIX + "Folder"
LINK_NAME = PREFIX + "Link"
DOCUMENT_NAME = PREFIX + "Document"
DIMENSION_NAMES = [
    PREFIX + 'Dimension1',
    PREFIX + 'Dimension2',
    PREFIX + 'Dimension3']


class TestDataMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

        # Build Dimensions
        for dimension_name in DIMENSION_NAMES:
            elements = [Element('Element {}'.format(str(j)), 'Numeric') for j in range(1, 1001)]
            element_attributes = [ElementAttribute("Attr1", "String"),
                                  ElementAttribute("Attr2", "Numeric"),
                                  ElementAttribute("Attr3", "Numeric")]
            hierarchy = Hierarchy(dimension_name=dimension_name,
                                  name=dimension_name,
                                  elements=elements,
                                  element_attributes=element_attributes)
            dimension = Dimension(dimension_name, [hierarchy])
            if cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.update(dimension)
            else:
                cls.tm1.dimensions.create(dimension)

        # Build Cube
        cube = Cube(CUBE_NAME, DIMENSION_NAMES)
        if not cls.tm1.cubes.exists(CUBE_NAME):
            cls.tm1.cubes.create(cube)

        # Build cube view
        view = NativeView(
            cube_name=CUBE_NAME,
            view_name=VIEW_NAME,
            suppress_empty_columns=True,
            suppress_empty_rows=True)
        view.add_row(
            dimension_name=DIMENSION_NAMES[0],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[0],
                expression='{[' + DIMENSION_NAMES[0] + '].Members}'))
        view.add_row(
            dimension_name=DIMENSION_NAMES[1],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[1],
                expression='{[' + DIMENSION_NAMES[1] + '].Members}'))
        view.add_column(
            dimension_name=DIMENSION_NAMES[2],
            subset=AnonymousSubset(
                dimension_name=DIMENSION_NAMES[2],
                expression='{[' + DIMENSION_NAMES[2] + '].Members}'))
        if not cls.tm1.cubes.views.exists(CUBE_NAME, view.name, private=False):
            cls.tm1.cubes.views.create(
                view=view,
                private=False)

        # Build subset
        subset = Subset(SUBSET_NAME, DIMENSION_NAMES[0], DIMENSION_NAMES[0], None, None, ["Element 1"])
        if cls.tm1.dimensions.hierarchies.subsets.exists(
                subset.name,
                subset.dimension_name,
                subset.hierarchy_name,
                False):
            cls.tm1.dimensions.hierarchies.subsets.delete(
                subset.name,
                subset.dimension_name,
                subset.hierarchy_name,
                False)
        cls.tm1.dimensions.hierarchies.subsets.create(subset, False)

        # Build process
        p1 = Process(name=PROCESS_NAME)
        p1.add_parameter('pRegion', 'pRegion (String)', value='US')
        if cls.tm1.processes.exists(p1.name):
            cls.tm1.processes.delete(p1.name)
        cls.tm1.processes.create(p1)

        # Build chore
        c1 = Chore(
            name=CHORE_NAME,
            start_time=ChoreStartTime(datetime.now().year, datetime.now().month, datetime.now().day,
                                      datetime.now().hour, datetime.now().minute, datetime.now().second),
            dst_sensitivity=False,
            active=True,
            execution_mode=Chore.MULTIPLE_COMMIT,
            frequency=ChoreFrequency(
                days=int(random.uniform(0, 355)),
                hours=int(random.uniform(0, 23)),
                minutes=int(random.uniform(0, 59)),
                seconds=int(random.uniform(0, 59))),
            tasks=[ChoreTask(0, PROCESS_NAME, parameters=[{'Name': 'pRegion', 'Value': 'UK'}])])
        cls.tm1.chores.create(c1)

        # create Folder
        app = FolderApplication("", TM1PY_APP_FOLDER)
        cls.tm1.applications.create(application=app, private=False)

    @classmethod
    def tearDownClass(cls) -> None:
        # delete view
        cls.tm1.cubes.views.delete(CUBE_NAME, VIEW_NAME, False)
        # delete cube
        cls.tm1.cubes.delete(CUBE_NAME)
        # delete dimensions
        for dimension_name in DIMENSION_NAMES:
            cls.tm1.dimensions.delete(dimension_name)
        # delete chore
        cls.tm1.chores.delete(CHORE_NAME)
        # delete process
        cls.tm1.processes.delete(PROCESS_NAME)
        # delete folder
        cls.tm1.applications.delete(
            path="",
            application_type=ApplicationTypes.FOLDER,
            application_name=TM1PY_APP_FOLDER,
            private=False)

    def run_test_cube_application(self, private):
        app = CubeApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, CUBE_NAME)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CUBE, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CUBE, private=private)
        self.assertFalse(exists)

    @unittest.skip
    def test_cube_application_private(self):
        self.run_test_cube_application(private=True)

    def test_cube_application_public(self):
        self.run_test_cube_application(private=False)

    def run_test_chore_application(self, private):
        app = ChoreApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, CHORE_NAME)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CHORE, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CHORE, private=private)
        self.assertFalse(exists)

    @unittest.skip
    def test_chore_application_private(self):
        self.run_test_chore_application(True)

    def test_chore_application_public(self):
        self.run_test_chore_application(False)

    def run_test_dimension_application(self, private=False):
        app = DimensionApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, DIMENSION_NAMES[0])
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DIMENSION, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DIMENSION, private=private)
        self.assertFalse(exists)

    @unittest.skip
    def test_dimension_application_private(self):
        self.run_test_dimension_application(private=True)

    def test_dimension_application_public(self):
        self.run_test_dimension_application(private=False)

    def run_test_document_application(self, private):
        with open(Path(__file__).parent.joinpath('resources', 'document.xlsx'), "rb") as file:
            app = DocumentApplication(path=TM1PY_APP_FOLDER, name=DOCUMENT_NAME, content=file.read())
            self.tm1.applications.create(application=app, private=private)

        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DOCUMENT, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DOCUMENT, private=private)
        self.assertFalse(exists)

    def test_document_application_private(self):
        self.run_test_document_application(private=True)

    def test_document_application_public(self):
        self.run_test_document_application(private=False)

    def run_test_folder_application(self, private):
        app = FolderApplication(TM1PY_APP_FOLDER, "not_relevant")
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.FOLDER, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.FOLDER, private=private)
        self.assertFalse(exists)

    def test_run_folder_application_private(self):
        self.run_test_folder_application(private=True)

    def test_run_folder_application_public(self):
        self.run_test_folder_application(private=False)

    def run_test_link_application(self, private):
        app = LinkApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, LINK_NAME)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.LINK, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.LINK, private=private)
        self.assertFalse(exists)

    def test_run_link_application_private(self):
        self.run_test_link_application(True)

    def test_run_link_application_public(self):
        self.run_test_link_application(False)

    def run_test_process_application(self, private):
        app = ProcessApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, PROCESS_NAME)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.PROCESS, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.PROCESS, private=private)
        self.assertFalse(exists)

    @unittest.skip
    def test_process_application_private(self):
        self.run_test_process_application(True)

    def test_process_application_public(self):
        self.run_test_process_application(False)

    def run_test_subset_application(self, private):
        app = SubsetApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, DIMENSION_NAMES[0], DIMENSION_NAMES[0], SUBSET_NAME)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.SUBSET, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.SUBSET, private=private)
        self.assertFalse(exists)

    @unittest.skip
    def test_subset_application_private(self):
        self.run_test_subset_application(True)

    def test_subset_application_public(self):
        self.run_test_subset_application(False)

    def run_test_view_application(self, private):
        app = ViewApplication(TM1PY_APP_FOLDER, APPLICATION_NAME, CUBE_NAME, VIEW_NAME)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.VIEW, private=private)
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.VIEW, private=private)
        self.assertFalse(exists)

    @unittest.skip
    def test_view_application_private(self):
        self.run_test_view_application(True)

    def test_view_application_public(self):
        self.run_test_view_application(False)
