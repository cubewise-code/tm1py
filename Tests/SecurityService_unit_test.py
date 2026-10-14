import json
import unittest
from unittest.mock import MagicMock

from TM1py.Services.SecurityService import SecurityService


def _mock_security_service(user_name: str, current_groups, known_groups):
    """A SecurityService wired to a MagicMock REST layer (no live server).

    GET answers the three lookups add_user_to_groups relies on: user name resolution,
    the user's current groups, and group name resolution. Group names are resolved
    against `known_groups` case-and-space-insensitively, like the server does.
    """
    rest = MagicMock()
    rest.is_security_admin = True

    def fake_get(url, **kwargs):
        response = MagicMock()
        if url.startswith("/Users?$filter"):
            response.json.return_value = {"value": [{"Name": user_name}]}
        elif url == f"/Users('{user_name}')/Groups":
            response.json.return_value = {"value": [{"Name": group} for group in current_groups]}
        elif url.startswith("/Groups?$filter"):
            requested = url.rsplit("'", 2)[1]
            matches = [g for g in known_groups if g.replace(" ", "").lower() == requested]
            response.json.return_value = {"value": [{"Name": g} for g in matches]}
        else:
            raise AssertionError(f"unexpected GET {url}")
        return response

    rest.GET.side_effect = fake_get
    return rest, SecurityService(rest)


def _bound_groups(rest):
    body = json.loads(rest.PATCH.call_args[0][1])
    return body["Groups@odata.bind"]


class TestAddUserToGroups(unittest.TestCase):

    def test_binds_union_of_existing_and_requested_groups(self):
        rest, security = _mock_security_service("Alice", ["Finance"], ["Finance", "Sales"])

        security.add_user_to_groups("alice", ["sales"])

        self.assertEqual(rest.PATCH.call_args[0][0], "/Users('Alice')")
        self.assertEqual(_bound_groups(rest), ["Groups('Finance')", "Groups('Sales')"])

    def test_requested_group_already_member_is_bound_once_with_server_casing(self):
        rest, security = _mock_security_service("Alice", ["Finance"], ["Finance", "Sales"])

        security.add_user_to_groups("Alice", ["FINANCE", "Sales"])

        self.assertEqual(_bound_groups(rest), ["Groups('Finance')", "Groups('Sales')"])

    def test_resolves_user_name_once(self):
        rest, security = _mock_security_service("Alice", ["Finance"], ["Finance", "Sales"])

        security.add_user_to_groups("alice", ["Sales"])

        user_lookups = [c for c in rest.GET.call_args_list if c[0][0].startswith("/Users?$filter")]
        self.assertEqual(len(user_lookups), 1)

    def test_skips_patch_when_user_already_in_all_requested_groups(self):
        rest, security = _mock_security_service("Alice", ["Finance", "Sales"], ["Finance", "Sales"])

        response = security.add_user_to_groups("Alice", ["finance", "SALES"])

        rest.PATCH.assert_not_called()
        self.assertIsNone(response)

    def test_skips_patch_when_no_groups_requested(self):
        rest, security = _mock_security_service("Alice", ["Finance"], ["Finance"])

        response = security.add_user_to_groups("Alice", [])

        rest.PATCH.assert_not_called()
        self.assertIsNone(response)

    def test_unknown_group_raises_before_patch(self):
        rest, security = _mock_security_service("Alice", ["Finance"], ["Finance"])

        with self.assertRaises(ValueError):
            security.add_user_to_groups("Alice", ["Nope"])

        rest.PATCH.assert_not_called()


if __name__ == "__main__":
    unittest.main()
