import unittest

import pytest
import requests
from requests.cookies import CookieConflictError, create_cookie

from TM1py.Services.RestService import RestService


class TestRestServiceCookies(unittest.TestCase):
    """Duplicate-scope cookie handling.

    `_start_session` re-sets 'TM1SessionId' without a domain/path, while TM1 itself
    issues one scoped to its domain and path. A jar holding both used to raise
    CookieConflictError on the next reconnect.
    """

    def setUp(self):
        # A real instance with only the cookie jar populated, rather than a mock:
        # both helpers touch nothing but self._s, and a stub would quietly answer
        # calls that a future signature change should break.
        self.rest = RestService.__new__(RestService)
        self.rest._s = requests.Session()

    def _add_unscoped(self, name, value):
        self.rest._s.cookies.set(name, value)

    def _add_scoped(self, name, value, domain="tm1.example.com", path="/api/v1"):
        self.rest._s.cookies.set_cookie(create_cookie(name, value, domain=domain, path=path))

    def test_duplicate_scopes_break_the_plain_jar_api(self):
        """Guards the premise: this is what the helpers exist to avoid.

        `RequestsCookieJar.pop`/`__getitem__` route through `_find_no_duplicates`,
        which raises rather than honouring the default once a name exists under
        two scopes -- a lookup failure, not a miss.
        """
        self._add_unscoped("TM1SessionId", "AAA")
        self._add_scoped("TM1SessionId", "BBB")

        with pytest.raises(CookieConflictError):
            self.rest._s.cookies.pop("TM1SessionId", None)
        with pytest.raises(CookieConflictError):
            self.rest._s.cookies["TM1SessionId"]

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

    def test_reset_cookie_stays_unscoped_for_reverse_proxies(self):
        """The re-set in _start_session must stay domain-less and path '/'.

        That is the whole point of the block: a reverse proxy can rewrite the
        request path, and a cookie scoped to the server's own '/api/v1' would
        simply not be sent to the rewritten URL. Keeping only the scoped copy
        silently unauthenticates every proxied call, so pin the scope here.
        """
        self._add_scoped("TM1SessionId", "FROM_SERVER")

        session_id = self.rest._pop_cookie("TM1SessionId")
        self.rest._s.cookies.set("TM1SessionId", session_id)

        cookie = next(c for c in self.rest._s.cookies if c.name == "TM1SessionId")
        self.assertEqual(cookie.domain, "")
        self.assertEqual(cookie.path, "/")
        self.assertEqual(cookie.value, "FROM_SERVER")

    def test_rotating_session_ids_keep_the_newest(self):
        """TM1 issues a fresh id on each connect; the newest must win.

        The scoped copy is the one the server just set, and the unscoped copy is
        the previous generation left behind by the last re-set. Preferring the
        unscoped one would pin the session to the first id forever.
        """
        for generation in range(1, 4):
            self._add_scoped("TM1SessionId", f"SRV{generation}")
            session_id = self.rest._pop_cookie("TM1SessionId")
            self.assertEqual(session_id, f"SRV{generation}")
            self.rest._s.cookies.set("TM1SessionId", session_id)

        self.assertEqual(self.rest._get_cookie("TM1SessionId"), "SRV3")


if __name__ == "__main__":
    unittest.main()
