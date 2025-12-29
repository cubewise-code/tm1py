import unittest

import responses

from TM1py.Services import TM1Service

DEFAULT_VERSION = "11.0.0"


class SmokeTestBase(unittest.TestCase):
    address = "tm1server"
    port = 8000
    protocol = "https"
    mocked_server_version = DEFAULT_VERSION

    def setUp(self):
        self.base_url = f"{self.protocol}://{self.address}:{self.port}/api/v1"
        self.rsps = responses.RequestsMock(assert_all_requests_are_fired=True)
        self.rsps.start()

        # Always stub ProductVersion before constructing TM1Service
        self.mock_bootstrap_version(self.mocked_server_version)

        # Construct service while mock is active
        self.tm1 = TM1Service(**self.get_tm1_kwargs())

    def tearDown(self):
        self.rsps.stop()
        self.rsps.reset()

    def get_tm1_kwargs(self):
        # Subclasses can override to tweak auth/args
        return {
            "address": self.address,
            "port": self.port,
            "user": "admin",
            "password": "apple",
            "ssl": True,
        }

    # Helpers for common stubs
    def mock_bootstrap_version(self, version: str = DEFAULT_VERSION):
        self.rsps.add(
            responses.GET,
            f"{self.base_url}/Configuration/ProductVersion/$value",
            body=version,
            status=200,
        )

    def mock_server_name(self, name: str):
        self.rsps.add(
            responses.GET,
            f"{self.base_url}/Configuration/ServerName/$value",
            body=name,
            status=200,
        )

    def mock_get(self, path: str, body: str, status: int = 200):
        # Generic helper if you need other endpoints
        self.rsps.add(responses.GET, f"{self.base_url}{path}", body=body, status=200)
