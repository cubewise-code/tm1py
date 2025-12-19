import configparser
import random
import unittest
from _datetime import datetime
from pathlib import Path

from TM1py import (
    AnonymousSubset,
    Chore,
    ChoreFrequency,
    ChoreStartTime,
    ChoreTask,
    Cube,
    Dimension,
    Element,
    ElementAttribute,
    Hierarchy,
    NativeView,
    Process,
    Subset,
    TM1Service,
)
from TM1py.Objects.Application import (
    Application,
    ApplicationTypes,
    ChoreApplication,
    CubeApplication,
    DimensionApplication,
    DocumentApplication,
    FolderApplication,
    LinkApplication,
    ProcessApplication,
    SubsetApplication,
    ViewApplication,
)

from .Utils import generate_test_uuid, skip_if_version_lower_than, verify_version


class TestApplicationService(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        cls.class_uuid = generate_test_uuid()

        cls.prefix = "TM1py_Tests_Applications_"
        cls.tm1py_app_folder = cls.prefix + "RootFolder_" + cls.class_uuid
        cls.cube_name = cls.prefix + "Cube_" + cls.class_uuid
        cls.view_name = cls.prefix + "View_" + cls.class_uuid
        cls.subset_name = cls.prefix + "Subset_" + cls.class_uuid
        cls.process_name = cls.prefix + "Process_" + cls.class_uuid
        cls.chore_name = cls.prefix + "Chore_" + cls.class_uuid
        cls.folder_name = cls.prefix + "Folder_" + cls.class_uuid
        cls.link_name = cls.prefix + "Link_" + cls.class_uuid
        cls.document_name = cls.prefix + "Document_" + cls.class_uuid
        cls.dimension_names = [
            cls.prefix + "Dimension1_" + cls.class_uuid,
            cls.prefix + "Dimension2_" + cls.class_uuid,
            cls.prefix + "Dimension3_" + cls.class_uuid,
        ]

        cls.rename_suffix = "_New"

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        # Build Dimensions
        for dimension_name in cls.dimension_names:
            elements = [Element(f"Element {j}", "Numeric") for j in range(1, 1001)]
            element_attributes = [
                ElementAttribute("Attr1", "String"),
                ElementAttribute("Attr2", "Numeric"),
                ElementAttribute("Attr3", "Numeric"),
            ]
            hierarchy = Hierarchy(
                dimension_name=dimension_name,
                name=dimension_name,
                elements=elements,
                element_attributes=element_attributes,
            )
            dimension = Dimension(dimension_name, [hierarchy])
            if cls.tm1.dimensions.exists(dimension.name):
                cls.tm1.dimensions.update(dimension)
            else:
                cls.tm1.dimensions.create(dimension)

        # Build Cube
        cube = Cube(cls.cube_name, cls.dimension_names)
        if not cls.tm1.cubes.exists(cls.cube_name):
            cls.tm1.cubes.create(cube)

        # Build cube view
        view = NativeView(
            cube_name=cls.cube_name, view_name=cls.view_name, suppress_empty_columns=True, suppress_empty_rows=True
        )
        view.add_row(
            dimension_name=cls.dimension_names[0],
            subset=AnonymousSubset(
                dimension_name=cls.dimension_names[0], expression="{[" + cls.dimension_names[0] + "].Members}"
            ),
        )
        view.add_row(
            dimension_name=cls.dimension_names[1],
            subset=AnonymousSubset(
                dimension_name=cls.dimension_names[1], expression="{[" + cls.dimension_names[1] + "].Members}"
            ),
        )
        view.add_column(
            dimension_name=cls.dimension_names[2],
            subset=AnonymousSubset(
                dimension_name=cls.dimension_names[2], expression="{[" + cls.dimension_names[2] + "].Members}"
            ),
        )
        if not cls.tm1.cubes.views.exists(cls.cube_name, view.name, private=False):
            cls.tm1.cubes.views.create(view=view, private=False)

        # Build subset
        subset = Subset(cls.subset_name, cls.dimension_names[0], cls.dimension_names[0], None, None, ["Element 1"])
        if cls.tm1.dimensions.hierarchies.subsets.exists(
            subset.name, subset.dimension_name, subset.hierarchy_name, False
        ):
            cls.tm1.dimensions.hierarchies.subsets.delete(
                subset.name, subset.dimension_name, subset.hierarchy_name, False
            )
        cls.tm1.dimensions.hierarchies.subsets.create(subset, False)

        # Build process
        p1 = Process(name=cls.process_name)
        p1.add_parameter("pRegion", "pRegion (String)", value="US")
        cls.tm1.processes.update_or_create(p1)

        # Build chore
        c1 = Chore(
            name=cls.chore_name,
            start_time=ChoreStartTime(
                datetime.now().year,
                datetime.now().month,
                datetime.now().day,
                datetime.now().hour,
                datetime.now().minute,
                datetime.now().second,
            ),
            dst_sensitivity=False,
            active=True,
            execution_mode=Chore.MULTIPLE_COMMIT,
            frequency=ChoreFrequency(
                days=int(random.uniform(0, 355)),
                hours=int(random.uniform(0, 23)),
                minutes=int(random.uniform(0, 59)),
                seconds=int(random.uniform(0, 59)),
            ),
            tasks=[ChoreTask(0, cls.process_name, parameters=[{"Name": "pRegion", "Value": "UK"}])],
        )
        cls.tm1.chores.update_or_create(c1)

        # create Folder
        app = FolderApplication("", cls.tm1py_app_folder)
        if cls.tm1.applications.exists(
            path=app.path, application_type=app.application_type, name=app.name, private=False
        ):
            cls.tm1.applications.delete(
                path=app.path, application_type=app.application_type, application_name=app.name, private=False
            )
            cls.tm1.applications.create(application=app, private=False)
        else:
            cls.tm1.applications.create(application=app, private=False)

    def setUp(self) -> None:
        test_uuid = generate_test_uuid()
        self.application_name = self.prefix + "Application_" + test_uuid

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up all test resources."""
        import logging

        cleanup_operations = [
            ("view", lambda: cls.tm1.cubes.views.delete(cls.cube_name, cls.view_name, False)),
            ("cube", lambda: cls.tm1.cubes.delete(cls.cube_name)),
            ("chore", lambda: cls.tm1.chores.delete(cls.chore_name)),
            ("process", lambda: cls.tm1.processes.delete(cls.process_name)),
            (
                "application folder",
                lambda: cls.tm1.applications.delete("", ApplicationTypes.FOLDER, cls.tm1py_app_folder, False),
            ),
        ]

        # Add dimension cleanup
        for dimension_name in cls.dimension_names:
            cleanup_operations.append(
                (f"dimension {dimension_name}", lambda d=dimension_name: cls.tm1.dimensions.delete(d))
            )

        # Execute all cleanup operations
        for description, operation in cleanup_operations:
            try:
                operation()
            except Exception as e:
                logging.debug(f"Failed to clean up {description}: {e}")

        cls.tm1.logout()

    def _run_application(self, app: Application, is_private: bool) -> None:

        self.tm1.applications.create(application=app, private=is_private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=is_private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=app.application_type, private=is_private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=app.application_type,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=is_private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=app.application_type, private=is_private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=app.application_type, private=is_private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=is_private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=app.application_type, private=is_private
        )
        self.assertFalse(exists)

    def test_cube_application_private(self):
        app = CubeApplication(self.tm1py_app_folder, self.application_name, self.cube_name)
        self._run_application(app, is_private=True)

    def test_cube_application_public(self):
        app = CubeApplication(self.tm1py_app_folder, self.application_name, self.cube_name)
        self._run_application(app, is_private=False)

    @unittest.skip
    def test_chore_application_private(self):
        app = ChoreApplication(self.tm1py_app_folder, self.application_name, self.chore_name)
        self._run_application(app, is_private=True)

    def test_chore_application_public(self):
        app = ChoreApplication(self.tm1py_app_folder, self.application_name, self.chore_name)
        self._run_application(app, is_private=False)

    def test_dimension_application_private(self):
        app = DimensionApplication(self.tm1py_app_folder, self.application_name, self.dimension_names[0])
        self._run_application(app, is_private=True)

    @skip_if_version_lower_than(version="11.4")
    def test_dimension_application_public(self):
        app = DimensionApplication(self.tm1py_app_folder, self.application_name, self.dimension_names[0])
        self._run_application(app, is_private=False)

    def _run_document_application(self, is_private: bool) -> None:
        with open(Path(__file__).parent.joinpath("resources", "document.xlsx"), "rb") as file:
            app = DocumentApplication(path=self.tm1py_app_folder, name=self.document_name, content=file.read())
            self.tm1.applications.create(application=app, private=is_private)

        self.tm1.applications.update_or_create(application=app, private=is_private)

        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=is_private)
        self.assertEqual(app_retrieved.last_updated[:10], datetime.today().strftime("%Y-%m-%d"))
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNotNone(app_retrieved.file_id)
        self.assertIsNotNone(app_retrieved.file_name)

        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=app.application_type, private=is_private
        )
        self.assertTrue(exists)

        names = self.tm1.applications.get_names(path=self.tm1py_app_folder, private=is_private)
        self.assertIn(app.name, names)

        self.tm1.applications.rename(
            app.path,
            application_type=app.application_type,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=is_private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=app.application_type, private=is_private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=app.application_type, private=is_private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=is_private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=app.application_type, private=is_private
        )
        self.assertFalse(exists)

    @skip_if_version_lower_than(version="11.4")
    def test_document_application_private(self):
        self._run_document_application(is_private=True)

    @skip_if_version_lower_than(version="11.4")
    def test_document_application_public(self):
        self._run_document_application(is_private=False)

    def test_run_folder_application_private(self):
        app = FolderApplication(self.tm1py_app_folder, "not_relevant")
        self._run_application(app, is_private=True)

    def test_run_folder_application_public(self):
        app = FolderApplication(self.tm1py_app_folder, "not_relevant")
        self._run_application(app, is_private=False)

    def test_run_link_application_private(self):
        app = LinkApplication(self.tm1py_app_folder, self.application_name, self.link_name)
        self._run_application(app, is_private=True)

    def test_run_link_application_public(self):
        app = LinkApplication(self.tm1py_app_folder, self.application_name, self.link_name)
        self._run_application(app, is_private=False)

    @unittest.skip
    def test_process_application_private(self):
        app = ProcessApplication(self.tm1py_app_folder, self.application_name, self.process_name)
        self._run_application(app, is_private=True)

    def test_process_application_public(self):
        app = ProcessApplication(self.tm1py_app_folder, self.application_name, self.process_name)
        self._run_application(app, is_private=False)

    @unittest.skip
    def test_subset_application_private(self):
        app = SubsetApplication(
            self.tm1py_app_folder,
            self.application_name,
            self.dimension_names[0],
            self.dimension_names[0],
            self.subset_name,
        )
        self._run_application(app, is_private=True)

    def test_subset_application_public(self):
        app = SubsetApplication(
            self.tm1py_app_folder,
            self.application_name,
            self.dimension_names[0],
            self.dimension_names[0],
            self.subset_name,
        )
        self._run_application(app, is_private=False)

    @unittest.skip
    def test_view_application_private(self):
        app = ViewApplication(self.tm1py_app_folder, self.application_name, self.cube_name, self.view_name)
        self._run_application(app, is_private=True)

    def test_view_application_public(self):
        app = ViewApplication(self.tm1py_app_folder, self.application_name, self.cube_name, self.view_name)
        self._run_application(app, is_private=False)
