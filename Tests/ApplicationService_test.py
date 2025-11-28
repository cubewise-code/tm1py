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

from .Utils import skip_if_version_lower_than, verify_version


class TestApplicationService(unittest.TestCase):
    tm1: TM1Service
    prefix = "TM1py_Tests_Applications_"
    tm1py_app_folder = prefix + "RootFolder"
    application_name = prefix + "Application"
    cube_name = prefix + "Cube"
    view_name = prefix + "View"
    subset_name = prefix + "Subset"
    process_name = prefix + "Process"
    chore_name = prefix + "Chore"
    folder_name = prefix + "Folder"
    link_name = prefix + "Link"
    document_name = prefix + "Document"
    dimension_names = [prefix + "Dimension1", prefix + "Dimension2", prefix + "Dimension3"]

    rename_suffix = "_New"

    @classmethod
    def setUpClass(cls) -> None:
        """
        Establishes a connection to TM1 and creates TM1 objects to use across all tests
        """

        # Connection to TM1
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        # Build Dimensions
        for dimension_name in cls.dimension_names:
            elements = [Element("Element {}".format(str(j)), "Numeric") for j in range(1, 1001)]
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

    @classmethod
    def tearDownClass(cls) -> None:
        # delete view
        cls.tm1.cubes.views.delete(cls.cube_name, cls.view_name, False)
        # delete cube
        cls.tm1.cubes.delete(cls.cube_name)
        # delete dimensions
        for dimension_name in cls.dimension_names:
            cls.tm1.dimensions.delete(dimension_name)
        # delete chore
        cls.tm1.chores.delete(cls.chore_name)
        # delete process
        cls.tm1.processes.delete(cls.process_name)
        # delete folder
        cls.tm1.applications.delete(
            path="", application_type=ApplicationTypes.FOLDER, application_name=cls.tm1py_app_folder, private=False
        )

    def run_cube_application(self, private):
        app = CubeApplication(self.tm1py_app_folder, self.application_name, self.cube_name)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CUBE, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.CUBE,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CUBE, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.CUBE, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.CUBE, private=private
        )
        self.assertFalse(exists)

    def test_cube_application_private(self):
        self.run_cube_application(private=True)

    def test_cube_application_public(self):
        self.run_cube_application(private=False)

    def run_chore_application(self, private):
        app = ChoreApplication(self.tm1py_app_folder, self.application_name, self.chore_name)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CHORE, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.CHORE,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.CHORE, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.CHORE, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.CHORE, private=private
        )
        self.assertFalse(exists)

    @unittest.skip
    def test_chore_application_private(self):
        self.run_chore_application(True)

    def test_chore_application_public(self):
        self.run_chore_application(False)

    def run_dimension_application(self, private=False):
        app = DimensionApplication(self.tm1py_app_folder, self.application_name, self.dimension_names[0])
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DIMENSION, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.DIMENSION,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DIMENSION, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.DIMENSION, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.DIMENSION, private=private
        )
        self.assertFalse(exists)

    def test_dimension_application_private(self):
        self.run_dimension_application(private=True)

    @skip_if_version_lower_than(version="11.4")
    def test_dimension_application_public(self):
        self.run_dimension_application(private=False)

    @skip_if_version_lower_than(version="11.4")
    def run_document_application(self, private):
        with open(Path(__file__).parent.joinpath("resources", "document.xlsx"), "rb") as file:
            app = DocumentApplication(path=self.tm1py_app_folder, name=self.document_name, content=file.read())
            self.tm1.applications.create(application=app, private=private)

        self.tm1.applications.update_or_create(application=app, private=private)

        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app_retrieved.last_updated[:10], datetime.today().strftime("%Y-%m-%d"))
        if not verify_version(required_version="12", version=self.tm1.version):
            self.assertIsNotNone(app_retrieved.file_id)
        self.assertIsNotNone(app_retrieved.file_name)

        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DOCUMENT, private=private
        )
        self.assertTrue(exists)

        names = self.tm1.applications.get_names(path=self.tm1py_app_folder, private=private)
        self.assertIn(app.name, names)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.DOCUMENT,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.DOCUMENT, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.DOCUMENT, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.DOCUMENT, private=private
        )
        self.assertFalse(exists)

    def test_document_application_private(self):
        self.run_document_application(private=True)

    def test_document_application_public(self):
        self.run_document_application(private=False)

    def run_folder_application(self, private):
        app = FolderApplication(self.tm1py_app_folder, "not_relevant")
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.FOLDER, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.FOLDER,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.FOLDER, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.FOLDER, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.FOLDER, private=private
        )
        self.assertFalse(exists)

    def test_run_folder_application_private(self):
        self.run_folder_application(private=True)

    def test_run_folder_application_public(self):
        self.run_folder_application(private=False)

    def run_link_application(self, private):
        app = LinkApplication(self.tm1py_app_folder, self.application_name, self.link_name)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.LINK, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.LINK,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.LINK, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.LINK, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.LINK, private=private
        )
        self.assertFalse(exists)

    def test_run_link_application_private(self):
        self.run_link_application(True)

    def test_run_link_application_public(self):
        self.run_link_application(False)

    def run_process_application(self, private):
        app = ProcessApplication(self.tm1py_app_folder, self.application_name, self.process_name)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.PROCESS, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.PROCESS,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.PROCESS, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.PROCESS, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.PROCESS, private=private
        )
        self.assertFalse(exists)

    @unittest.skip
    def test_process_application_private(self):
        self.run_process_application(True)

    def test_process_application_public(self):
        self.run_process_application(False)

    def run_subset_application(self, private):
        app = SubsetApplication(
            self.tm1py_app_folder,
            self.application_name,
            self.dimension_names[0],
            self.dimension_names[0],
            self.subset_name,
        )
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.SUBSET, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.SUBSET,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.SUBSET, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.SUBSET, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.SUBSET, private=private
        )
        self.assertFalse(exists)

    @unittest.skip
    def test_subset_application_private(self):
        self.run_subset_application(True)

    def test_subset_application_public(self):
        self.run_subset_application(False)

    def run_view_application(self, private):
        app = ViewApplication(self.tm1py_app_folder, self.application_name, self.cube_name, self.view_name)
        self.tm1.applications.create(application=app, private=private)
        app_retrieved = self.tm1.applications.get(app.path, app.application_type, app.name, private=private)
        self.assertEqual(app, app_retrieved)
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.VIEW, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.rename(
            app.path,
            application_type=ApplicationTypes.VIEW,
            application_name=app.name,
            new_application_name=app.name + self.rename_suffix,
            private=private,
        )
        exists = self.tm1.applications.exists(
            app.path, name=app.name, application_type=ApplicationTypes.VIEW, private=private
        )
        self.assertFalse(exists)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.VIEW, private=private
        )
        self.assertTrue(exists)

        self.tm1.applications.delete(app.path, app.application_type, app.name + self.rename_suffix, private=private)
        exists = self.tm1.applications.exists(
            app.path, name=app.name + self.rename_suffix, application_type=ApplicationTypes.VIEW, private=private
        )
        self.assertFalse(exists)

    @unittest.skip
    def test_view_application_private(self):
        self.run_view_application(True)

    def test_view_application_public(self):
        self.run_view_application(False)

    # Tests for private path resolution functionality

    def test_build_path_url_all_public(self):
        """Test _build_path_url with all public segments"""
        segments = ["Folder1", "Folder2", "Folder3"]
        result = self.tm1.applications._build_path_url(segments, private_from=None)
        expected = "/Contents('Folder1')/Contents('Folder2')/Contents('Folder3')"
        self.assertEqual(result, expected)

    def test_build_path_url_all_private(self):
        """Test _build_path_url with all private segments"""
        segments = ["Folder1", "Folder2", "Folder3"]
        result = self.tm1.applications._build_path_url(segments, private_from=0)
        expected = "/PrivateContents('Folder1')/PrivateContents('Folder2')/PrivateContents('Folder3')"
        self.assertEqual(result, expected)

    def test_build_path_url_mixed_boundary_at_1(self):
        """Test _build_path_url with private boundary at index 1"""
        segments = ["Folder1", "Folder2", "Folder3"]
        result = self.tm1.applications._build_path_url(segments, private_from=1)
        expected = "/Contents('Folder1')/PrivateContents('Folder2')/PrivateContents('Folder3')"
        self.assertEqual(result, expected)

    def test_build_path_url_mixed_boundary_at_2(self):
        """Test _build_path_url with private boundary at index 2"""
        segments = ["Folder1", "Folder2", "Folder3"]
        result = self.tm1.applications._build_path_url(segments, private_from=2)
        expected = "/Contents('Folder1')/Contents('Folder2')/PrivateContents('Folder3')"
        self.assertEqual(result, expected)

    def test_build_path_url_empty_segments(self):
        """Test _build_path_url with empty segments list"""
        segments = []
        result = self.tm1.applications._build_path_url(segments, private_from=None)
        self.assertEqual(result, "")

    def test_build_path_url_single_segment_public(self):
        """Test _build_path_url with single public segment"""
        segments = ["Folder1"]
        result = self.tm1.applications._build_path_url(segments, private_from=None)
        expected = "/Contents('Folder1')"
        self.assertEqual(result, expected)

    def test_build_path_url_single_segment_private(self):
        """Test _build_path_url with single private segment"""
        segments = ["Folder1"]
        result = self.tm1.applications._build_path_url(segments, private_from=0)
        expected = "/PrivateContents('Folder1')"
        self.assertEqual(result, expected)

    def test_build_path_url_special_characters(self):
        """Test _build_path_url handles special characters in folder names"""
        segments = ["Folder's Name", "Folder & Co"]
        result = self.tm1.applications._build_path_url(segments, private_from=None)
        # format_url should escape single quotes
        self.assertIn("Folder''s Name", result)

    def test_private_folder_get_names(self):
        """Test get_names on a private folder at root level"""
        # Create a private folder
        private_folder_name = self.prefix + "PrivateFolder"
        private_folder = FolderApplication("", private_folder_name)

        # Clean up if exists
        if self.tm1.applications.exists(
            path="", application_type=ApplicationTypes.FOLDER, name=private_folder_name, private=True
        ):
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )

        # Create private folder
        self.tm1.applications.create(application=private_folder, private=True)

        try:
            # Create a link application inside the private folder
            link_app = LinkApplication(private_folder_name, self.application_name, "http://example.com")
            self.tm1.applications.create(application=link_app, private=True)

            # Test get_names - should auto-resolve the private path
            names = self.tm1.applications.get_names(path=private_folder_name, private=True)
            self.assertIn(self.application_name, names)

            # Clean up link
            self.tm1.applications.delete(
                path=private_folder_name,
                application_type=ApplicationTypes.LINK,
                application_name=self.application_name,
                private=True,
            )
        finally:
            # Clean up private folder
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )

    def test_private_folder_exists(self):
        """Test exists on an application inside a private folder"""
        # Create a private folder
        private_folder_name = self.prefix + "PrivateFolder2"
        private_folder = FolderApplication("", private_folder_name)

        # Clean up if exists
        if self.tm1.applications.exists(
            path="", application_type=ApplicationTypes.FOLDER, name=private_folder_name, private=True
        ):
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )

        # Create private folder
        self.tm1.applications.create(application=private_folder, private=True)

        try:
            # Create a link application inside the private folder
            link_app = LinkApplication(private_folder_name, self.application_name, "http://example.com")
            self.tm1.applications.create(application=link_app, private=True)

            # Test exists - should auto-resolve the private path
            exists = self.tm1.applications.exists(
                path=private_folder_name,
                application_type=ApplicationTypes.LINK,
                name=self.application_name,
                private=True,
            )
            self.assertTrue(exists)

            # Clean up link
            self.tm1.applications.delete(
                path=private_folder_name,
                application_type=ApplicationTypes.LINK,
                application_name=self.application_name,
                private=True,
            )
        finally:
            # Clean up private folder
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )

    def test_private_folder_with_cache(self):
        """Test that caching works for private path resolution"""
        # Create a private folder
        private_folder_name = self.prefix + "PrivateFolderCache"
        private_folder = FolderApplication("", private_folder_name)

        # Clean up if exists
        if self.tm1.applications.exists(
            path="", application_type=ApplicationTypes.FOLDER, name=private_folder_name, private=True
        ):
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )

        # Create private folder
        self.tm1.applications.create(application=private_folder, private=True)

        try:
            # Create a link application inside the private folder
            link_app = LinkApplication(private_folder_name, self.application_name, "http://example.com")
            self.tm1.applications.create(application=link_app, private=True)

            # Clear cache
            self.tm1.applications._private_path_cache.clear()

            # First call - should populate cache
            names1 = self.tm1.applications.get_names(path=private_folder_name, private=True, use_cache=True)
            self.assertIn(self.application_name, names1)

            # Verify cache was populated
            self.assertIn(private_folder_name, self.tm1.applications._private_path_cache)

            # Second call - should use cache
            names2 = self.tm1.applications.get_names(path=private_folder_name, private=True, use_cache=True)
            self.assertEqual(names1, names2)

            # Clean up link
            self.tm1.applications.delete(
                path=private_folder_name,
                application_type=ApplicationTypes.LINK,
                application_name=self.application_name,
                private=True,
            )
        finally:
            # Clean up private folder
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )
            # Clear cache
            self.tm1.applications._private_path_cache.clear()

    def test_nested_private_folder(self):
        """Test accessing applications in nested private folders"""
        # Create a private folder with a subfolder
        private_folder_name = self.prefix + "PrivateFolderNested"
        subfolder_name = self.prefix + "SubFolder"
        private_folder = FolderApplication("", private_folder_name)
        subfolder = FolderApplication(private_folder_name, subfolder_name)

        # Clean up if exists
        if self.tm1.applications.exists(
            path="", application_type=ApplicationTypes.FOLDER, name=private_folder_name, private=True
        ):
            # Try to delete subfolder first
            try:
                self.tm1.applications.delete(
                    path=private_folder_name,
                    application_type=ApplicationTypes.FOLDER,
                    application_name=subfolder_name,
                    private=True,
                )
            except Exception:
                pass
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )

        # Create private folder and subfolder
        self.tm1.applications.create(application=private_folder, private=True)
        self.tm1.applications.create(application=subfolder, private=True)

        try:
            # Create a link application inside the nested folder
            nested_path = f"{private_folder_name}/{subfolder_name}"
            link_app = LinkApplication(nested_path, self.application_name, "http://example.com")
            self.tm1.applications.create(application=link_app, private=True)

            # Test get_names on nested path - should auto-resolve
            names = self.tm1.applications.get_names(path=nested_path, private=True)
            self.assertIn(self.application_name, names)

            # Test exists on nested path
            exists = self.tm1.applications.exists(
                path=nested_path,
                application_type=ApplicationTypes.LINK,
                name=self.application_name,
                private=True,
            )
            self.assertTrue(exists)

            # Clean up link
            self.tm1.applications.delete(
                path=nested_path,
                application_type=ApplicationTypes.LINK,
                application_name=self.application_name,
                private=True,
            )
        finally:
            # Clean up folders
            try:
                self.tm1.applications.delete(
                    path=private_folder_name,
                    application_type=ApplicationTypes.FOLDER,
                    application_name=subfolder_name,
                    private=True,
                )
            except Exception:
                pass
            self.tm1.applications.delete(
                path="", application_type=ApplicationTypes.FOLDER, application_name=private_folder_name, private=True
            )
