from .SmokeTestBase import SmokeTestBase


class TestConnectionSmoke(SmokeTestBase):

    def test_tm1_connection(self):
        tm1_version = self.tm1.configuration.get_product_version()
        self.assertEqual(tm1_version, self.mocked_server_version)

    def test_tm1_server_name(self):
        self.mock_server_name("Tm1pyMockedDatabase")
        server_name = self.tm1.configuration.get_server_name()
        self.assertEqual(server_name, "Tm1pyMockedDatabase")

    def test_is_connected(self):
        self.mock_server_name("Tm1pyMockedDatabase")
        self.assertTrue(self.tm1.connection.is_connected())
