import configparser
import os
import unittest

from TM1py.Exceptions.Exceptions import TM1pyException
from TM1py.Services import TM1Service

CONFIG_SECTION_SRV01 = 'tm1srv01'
config_with_credentials = configparser.ConfigParser()
config_with_credentials.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))
config_with_token = configparser.ConfigParser()
config_with_token.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.ini'))
config_with_token.set(CONFIG_SECTION_SRV01, 'user', '')
config_with_token.set(CONFIG_SECTION_SRV01, 'password', '')


class TestConnection(unittest.TestCase):
    def test_closing_when_retain_not_required(self):
        config_with_credentials.set(CONFIG_SECTION_SRV01, 'retain_connection', 'False')
        with TM1Service(**config_with_credentials[CONFIG_SECTION_SRV01]) as tm1:
            self.assertIsNotNone(tm1.whoami, 'Not connected')
            session = tm1.connection.session_id
            config_with_token.set(CONFIG_SECTION_SRV01, 'session_id', session)
        # the context manager should call __exit__ at this point on TM1Server and RESTService objects
        with self.assertRaises(TM1pyException):
            with TM1Service(**config_with_token[CONFIG_SECTION_SRV01]) as tm1:
                self.assertIsNone(tm1.whoami, 'Not connected')

    def test_closing_when_retain_required(self):
        config_with_credentials.set(CONFIG_SECTION_SRV01, 'retain_connection', 'True')
        with TM1Service(**config_with_credentials[CONFIG_SECTION_SRV01]) as tm1:
            self.assertIsNotNone(tm1.connection.session_id, 'Not connected')
            session = tm1.connection.session_id
            config_with_token.set(CONFIG_SECTION_SRV01, 'session_id', session)
        # the context manager should call __exit__ at this point on TM1Server and RESTService objects
        with TM1Service(**config_with_token[CONFIG_SECTION_SRV01]) as tm1:
            self.assertEqual(tm1.connection.session_id, session, 'Session differs')
            tm1.logout()


if __name__ == '__main__':
    unittest.main()
