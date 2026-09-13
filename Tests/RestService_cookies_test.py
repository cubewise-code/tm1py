import unittest
from unittest.mock import MagicMock

import requests
from requests.cookies import create_cookie

from TM1py.Services.RestService import RestService


class TestRestServiceCookies(unittest.TestCase):
    """Duplicate-scope cookie handling.

    `_start_session` re-sets 'TM1SessionId' without a domain/path, while TM1 itself
    issues one scoped to its domain and path. A jar holding both used to raise
    CookieConflictError on the next reconnect.
    """

    def setUp(self):
        self.rest = MagicMock(spec=RestService)
        self.rest._s = requests.Session()
        # bind the real implementations onto the mock
        self.rest._get_cookie = RestService._get_cookie.__get__(self.rest)
        self.rest._pop_cookie = RestService._pop_cookie.__get__(self.rest)

    def _add_unscoped(self, name, value):
        self.rest._s.cookies.set(name, value)

    def _add_scoped(self, name, value, domain="tm1.example.com", path="/api/v1"):
        self.rest._s.cookies.set_cookie(create_cookie(name, value, domain=domain, path=path))

    def test_get_cookie_single(self):
        self._add_unscoped("TM1SessionId", "AAA")
        self.assertEqual(self.rest._get_cookie("TM1SessionId"), "AAA")

    def test_get_cookie_prefers_scoped_duplicate(self):
        self._add_unscoped("TM1SessionId", "AAA")
        self._add_scoped("TM1SessionId", "BBB")
        self.assertEqual(self.rest._get_cookie("TM1SessionId"), "BBB")

    def test_get_cookie_missing_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.rest._get_cookie("TM1SessionId")

    def test_pop_cookie_missing_returns_none(self):
        self.assertIsNone(self.rest._pop_cookie("TM1SessionId"))

    def test_pop_cookie_clears_all_scopes(self):
        self._add_unscoped("TM1SessionId", "AAA")
        self._add_scoped("TM1SessionId", "BBB")

        self.assertEqual(self.rest._pop_cookie("TM1SessionId"), "BBB")
        self.assertEqual([c for c in self.rest._s.cookies if c.name == "TM1SessionId"], [])

    def test_pop_cookie_leaves_other_cookies(self):
        self._add_unscoped("TM1SessionId", "AAA")
        self._add_unscoped("paSession", "KEEP")

        self.rest._pop_cookie("TM1SessionId")
        self.assertEqual(self.rest._get_cookie("paSession"), "KEEP")

    def test_reconnect_cycle_does_not_raise(self):
        """The reported failure: repeated connect/reconnect must stay stable."""
        for _ in range(5):
            session_id = self.rest._pop_cookie("TM1SessionId")
            if session_id is not None:
                self.rest._s.cookies.set("TM1SessionId", session_id)
            # TM1 replies with its own scoped cookie on every connect
            self._add_scoped("TM1SessionId", "FROM_SERVER")

        self.assertEqual(self.rest._get_cookie("TM1SessionId"), "FROM_SERVER")

    def test_session_id_property_with_duplicates(self):
        self._add_unscoped("TM1SessionId", "AAA")
        self._add_scoped("TM1SessionId", "BBB")
        self.assertEqual(RestService.session_id.fget(self.rest), "BBB")

    def test_session_id_property_falls_back_to_pasession(self):
        self._add_unscoped("paSession", "V12")
        self.assertEqual(RestService.session_id.fget(self.rest), "V12")


if __name__ == "__main__":
    unittest.main()
