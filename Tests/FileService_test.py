import configparser
import unittest
from pathlib import Path

from TM1py import TM1Service
from .Utils import skip_if_insufficient_version


class TestApplicationService(unittest.TestCase):
    tm1: TM1Service

    FILE_NAME1 = "TM1py_unittest_file1"
    FILE_NAME2 = "TM1py_unittest_file2"

    @classmethod
    def setUp(cls) -> None:
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath('config.ini'))
        cls.tm1 = TM1Service(**cls.config['tm1srv01'])

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as file:
            cls.tm1.files.update_or_create(cls.FILE_NAME1, file.read())

        if cls.tm1.files.exists(cls.FILE_NAME2):
            cls.tm1.files.delete(cls.FILE_NAME2)

    @skip_if_insufficient_version(version="11.4")
    def test_create_get(self):
        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.tm1.files.create(self.FILE_NAME2, original_file.read())

            created_file = self.tm1.files.get(self.FILE_NAME1)

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.assertEqual(original_file.read(), created_file)

    @skip_if_insufficient_version(version="11.4")
    def test_update_get(self):
        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.tm1.files.update(self.FILE_NAME1, original_file.read())

            created_file = self.tm1.files.get(self.FILE_NAME1)

        with open(Path(__file__).parent.joinpath('resources', 'file.csv'), "rb") as original_file:
            self.assertEqual(original_file.read(), created_file)

    @skip_if_insufficient_version(version="11.4")
    def test_delete_exists(self):
        self.assertTrue(self.tm1.files.exists(self.FILE_NAME1))

        self.tm1.files.delete(self.FILE_NAME1)

        self.assertFalse(self.tm1.files.exists(self.FILE_NAME1))

    def tearDown(self) -> None:
        if self.tm1.files.exists(self.FILE_NAME1):
            self.tm1.files.delete(self.FILE_NAME1)
        if self.tm1.files.exists(self.FILE_NAME2):
            self.tm1.files.delete(self.FILE_NAME2)
