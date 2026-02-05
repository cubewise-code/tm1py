import configparser
import time
import unittest
from pathlib import Path

import pytest

from TM1py.Services import ManageService, TM1Service

from .Utils import verify_version


class TestManagerService(unittest.TestCase):
    manager: ManageService
    instance = "TM1py_tests_instance"
    database = "TM1py_tests_database"
    application = "TM1py_tests_application"
    backup_set = f"{database}_backup"
    starting_replicas = 0
    cpu_requests = "1000m"
    cpu_limits = "2000m"
    memory_requests = "1G"
    memory_limits = "2G"
    storage_size = "20Gi"
    version = "12.3.4"
    application_client = None
    application_secret = None

    @classmethod
    def setUpClass(cls):
        """
        Establishes a connection to the manager endpoint and creates a testing environment
        """
        # Manager Connection
        cls.config = configparser.ConfigParser()
        cls.config.read(Path(__file__).parent.joinpath("config.ini"))
        connection_details = cls.config["tm1srv01"]

        # Connect to TM1 to get server versions.
        cls.tm1 = TM1Service(**cls.config["tm1srv01"])

        if verify_version(required_version="12.0.0", version=cls.tm1.version):

            cls.manager = ManageService(
                domain=connection_details["domain"],
                root_client=connection_details["root_client"],
                root_secret=connection_details["root_secret"],
            )

            # Cleanup and Create New Instance
            if cls.manager.instance_exists(instance_name=cls.instance):
                cls.manager.delete_instance(instance_name=cls.instance)
            cls.manager.create_instance(instance_name=cls.instance)

            # Cleanup and Create New Database
            if cls.manager.database_exists(instance_name=cls.instance, database_name=cls.database):
                cls.manager.delete_database(instance_name=cls.instance, database_name=cls.database)
            cls.manager.create_database(
                instance_name=cls.instance,
                database_name=cls.database,
                product_version=cls.version,
                number_replicas=cls.starting_replicas,
                cpu_requests=cls.cpu_requests,
                cpu_limits=cls.cpu_limits,
                memory_limits=cls.memory_limits,
                memory_requests=cls.memory_requests,
                storage_size=cls.storage_size,
            )
        else:
            raise unittest.SkipTest(
                f"Skipping all Manager Service tests, version minimum not met, " f"12.0.0 > {cls.tm1.version}"
            )

    @classmethod
    def tearDownClass(cls):
        cls.manager.delete_database(instance_name=cls.instance, database_name=cls.database)
        cls.manager.delete_instance(instance_name=cls.instance)

    @pytest.mark.skip(reason="Not supported in PAaaS")
    def test_get_instance(self):
        instance = self.manager.get_instance(instance_name=self.instance)
        self.assertEqual(self.instance, instance.get("Name"))

    @pytest.mark.skip(reason="Not supported in PAaaS")
    def test_get_database(self):
        database = self.manager.get_database(instance_name=self.instance, database_name=self.database)
        self.assertEqual(self.database, database.get("Name"))

    @pytest.mark.skip(reason="Too slow for regular tests. Only run before releases")
    def test_scale_database(self):
        self.manager.scale_database(
            instance_name=self.instance, database_name=self.database, replicas=(self.starting_replicas + 1)
        )

        replicas = self.manager.get_database(instance_name=self.instance, database_name=self.database).get("Replicas")

        self.assertEqual(replicas, (self.starting_replicas + 1))

        time.sleep(30)

        self.manager.scale_database(
            instance_name=self.instance, database_name=self.database, replicas=self.starting_replicas
        )

        replicas = self.manager.get_database(instance_name=self.instance, database_name=self.database).get("Replicas")

        self.assertEqual(replicas, self.starting_replicas)

    @pytest.mark.skip(reason="Not supported in PAaaS")
    def test_create_and_get_application(self):

        # Create Application and Store Credentials
        self.clientID, self.clientSecret = self.manager.create_application(
            instance_name=self.instance, application_name=self.application
        )

        self.assertIsNotNone(self.clientID)
        self.assertIsNotNone(self.clientSecret)

        application = self.manager.get_application(instance_name=self.instance, application_name=self.application)

        self.assertEqual(self.application, application.get("Name"))

    @pytest.mark.skip(reason="Too slow for regular tests. Only run before releases")
    def test_create_backup_set(self):

        response = self.manager.create_database_backup(
            instance_name=self.instance, database_name=self.database, backup_set_name=self.backup_set
        )

        self.assertTrue(response.ok)


if __name__ == "__main__":
    unittest.main(failfast=True)
