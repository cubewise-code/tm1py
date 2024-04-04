import configparser
import unittest
from pathlib import Path

from TM1py import TM1Service
from .Utils import skip_if_insufficient_version


class TestFileService(unittest.TestCase):
    tm1: TM1Service

    FILE_NAME1 = "TM1py_unittest_file1"
    FILE_NAME2 = "TM1py_unittest_file2"

    FILE_NAME1_IN_FOLDER = Path("TM1py") / "Tests" / FILE_NAME1
    FILE_NAME2_IN_FOLDER = Path("TM1py") / "Tests" / FILE_NAME2

    def setUp(self) -> None:
        self.config = configparser.ConfigParser()
        self.config.read(Path(__file__).parent.joinpath('config.ini'))
        self.tm1 = TM1Service(**self.config['tm1srv01'])

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as file:
            self.tm1.files.update_or_create(self.FILE_NAME1, file.read())
            self.tm1.files.update_or_create(self.FILE_NAME1_IN_FOLDER, file.read())

        if self.tm1.files.exists(self.FILE_NAME2):
            self.tm1.files.delete(self.FILE_NAME2)
        if self.tm1.files.exists(self.FILE_NAME2_IN_FOLDER):
            self.tm1.files.delete(self.FILE_NAME2_IN_FOLDER)

    @skip_if_insufficient_version(version="11.4")
    def test_create_get(self):
        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.tm1.files.update_or_create(self.FILE_NAME1, original_file.read())

            created_file = self.tm1.files.get(self.FILE_NAME1)

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.assertEqual(original_file.read(), created_file)

    @skip_if_insufficient_version(version="12")
    def test_create_get_in_folder(self):
        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.tm1.files.update_or_create(self.FILE_NAME1_IN_FOLDER, original_file.read())

            created_file = self.tm1.files.get(self.FILE_NAME1_IN_FOLDER)

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.assertEqual(original_file.read(), created_file)

    @skip_if_insufficient_version(version="11.4")
    def test_update_get(self):
        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.tm1.files.update(self.FILE_NAME1, original_file.read())

            created_file = self.tm1.files.get(self.FILE_NAME1)

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.assertEqual(original_file.read(), created_file)

    @skip_if_insufficient_version(version="12")
    def test_update_get_in_folder(self):
        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.tm1.files.update(self.FILE_NAME1_IN_FOLDER, original_file.read())

            created_file = self.tm1.files.get(self.FILE_NAME1_IN_FOLDER)

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.assertEqual(original_file.read(), created_file)

    @skip_if_insufficient_version(version="11.4")
    def test_get_all_names(self):
        result = self.tm1.files.get_all_names()
        self.assertIn(self.FILE_NAME1, result)

    @skip_if_insufficient_version(version="12")
    def test_get_all_names_in_folder(self):
        result = self.tm1.files.get_all_names(path=self.FILE_NAME1_IN_FOLDER.parent)
        self.assertIn(self.FILE_NAME1, result)

    @skip_if_insufficient_version(version="11.4")
    def test_search_string_in_name__name_startswith(self):
        result = self.tm1.files.search_string_in_name(name_startswith=self.FILE_NAME1)
        self.assertEqual([self.FILE_NAME1], result)

    @skip_if_insufficient_version(version="12")
    def test_search_string_in_name__name_startswith_in_folder(self):
        result = self.tm1.files.search_string_in_name(
            name_startswith=self.FILE_NAME1,
            path=self.FILE_NAME1_IN_FOLDER.parent)
        self.assertEqual([self.FILE_NAME1], result)

    @skip_if_insufficient_version(version="11.4")
    def test_search_string_in_name__name_startswith_not_existing(self):
        result = self.tm1.files.search_string_in_name(name_startswith='not_the_file_im_looking_for')
        self.assertEqual([], result)

    @skip_if_insufficient_version(version="11.4")
    def test_search_string_in_name__name_contains_both_existing(self):
        result = self.tm1.files.search_string_in_name(name_contains=[self.FILE_NAME1[:5], self.FILE_NAME1[-5:]])
        self.assertEqual([self.FILE_NAME1], result)

    @skip_if_insufficient_version(version="11.4")
    def test_search_string_in_name__name_contains_mixed_existing_and(self):
        result = self.tm1.files.search_string_in_name(name_contains=[self.FILE_NAME1[:5], 'NotFound'])
        self.assertEqual([], result)

    @skip_if_insufficient_version(version="11.4")
    def test_search_string_in_name__name_contains_mixed_existing_or(self):
        result = self.tm1.files.search_string_in_name(
            name_contains=[self.FILE_NAME1, 'NotFound'],
            name_contains_operator='OR')
        self.assertEqual([self.FILE_NAME1], result)

    @skip_if_insufficient_version(version="11.4")
    def test_delete_exists(self):
        self.assertTrue(self.tm1.files.exists(self.FILE_NAME1))

        self.tm1.files.delete(self.FILE_NAME1)

        self.assertFalse(self.tm1.files.exists(self.FILE_NAME1))

    @skip_if_insufficient_version(version="12")
    def test_delete_exists_in_folder(self):
        self.assertTrue(self.tm1.files.exists(self.FILE_NAME1_IN_FOLDER))

        self.tm1.files.delete(self.FILE_NAME1_IN_FOLDER)

        self.assertFalse(self.tm1.files.exists(self.FILE_NAME1_IN_FOLDER))

    def tearDown(self) -> None:
        if self.tm1.files.exists(self.FILE_NAME1):
            self.tm1.files.delete(self.FILE_NAME1)
        if self.tm1.files.exists(self.FILE_NAME2):
            self.tm1.files.delete(self.FILE_NAME2)
        if self.tm1.files.exists(self.FILE_NAME1_IN_FOLDER):
            self.tm1.files.delete(self.FILE_NAME1_IN_FOLDER)
        if self.tm1.files.exists(self.FILE_NAME2_IN_FOLDER):
            self.tm1.files.delete(self.FILE_NAME2_IN_FOLDER)
        self.tm1.logout()
