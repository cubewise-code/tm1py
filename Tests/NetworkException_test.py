# -*- coding: utf-8 -*-

import unittest

from requests import Response

from TM1py.Exceptions.Exceptions import (
    TM1pyException,
    TM1pyNetworkException,
    TM1pyRestException,
)
from TM1py.Services.RestService import RestService

CLOUDFLARE_HTML_WITH_RAY_ID = """<!DOCTYPE html>
<html>
<head><title>Attention Required! | Cloudflare</title></head>
<body>
<h1>You have been blocked</h1>
<p>Sorry, you have been blocked from accessing this resource.</p>
<p>Cloudflare Ray ID: 9ef02047ab37aac9</p>
</body>
</html>"""

CLOUDFLARE_HTML_COLON_FORMAT = """<!DOCTYPE html>
<html>
<body>
<p>Ray ID: abc123def456</p>
</body>
</html>"""

CLOUDFLARE_HTML_SPACE_FORMAT = """<!DOCTYPE html>
<html>
<body>
<p>Ray ID abc123def456</p>
</body>
</html>"""

GENERIC_HTML_NO_RAY_ID = """<!DOCTYPE html>
<html>
<head><title>502 Bad Gateway</title></head>
<body>
<h1>502 Bad Gateway</h1>
<p>nginx</p>
</body>
</html>"""

SAMPLE_HEADERS = {"Content-Type": "text/html", "Connection": "keep-alive"}

class TestNetworkException(unittest.TestCase):

    # Instantiation & properties                                
    def test_status_code_property(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.status_code, 403)

    def test_reason_property(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.reason, "Forbidden")

    def test_headers_property(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.headers, SAMPLE_HEADERS)

    def test_response_property_mirrors_message(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.response, exc.message)
        self.assertEqual(exc.response, GENERIC_HTML_NO_RAY_ID)

    # __str__test
    def test_str_without_ray_id(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=502,
            reason="Bad Gateway",
            headers=SAMPLE_HEADERS,
        )
        result = str(exc)
        self.assertIn("502", result)
        self.assertIn("Bad Gateway", result)
        self.assertNotIn("Cloudflare Ray ID", result)

    def test_str_with_ray_id(self):
        exc = TM1pyNetworkException(
            response=CLOUDFLARE_HTML_WITH_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        result = str(exc)
        self.assertIn("403", result)
        self.assertIn("Forbidden", result)
        self.assertIn("9ef02047ab37aac9", result)
        self.assertIn("Cloudflare Ray ID", result)


    # Ray ID extraction                                            
    def test_ray_id_extracted_with_colon_format(self):
        exc = TM1pyNetworkException(
            response=CLOUDFLARE_HTML_COLON_FORMAT,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.ray_id, "abc123def456")

    def test_ray_id_extracted_with_space_format(self):
        exc = TM1pyNetworkException(
            response=CLOUDFLARE_HTML_SPACE_FORMAT,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.ray_id, "abc123def456")

    def test_ray_id_extracted_from_real_cloudflare_html(self):
        exc = TM1pyNetworkException(
            response=CLOUDFLARE_HTML_WITH_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertEqual(exc.ray_id, "9ef02047ab37aac9")

    def test_ray_id_is_none_for_generic_html(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=502,
            reason="Bad Gateway",
            headers=SAMPLE_HEADERS,
        )
        self.assertIsNone(exc.ray_id)

    def test_ray_id_is_none_for_empty_response(self):
        exc = TM1pyNetworkException(
            response="",
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertIsNone(exc.ray_id)


    # Inheritance test         
    def test_is_instance_of_tm1py_exception(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertIsInstance(exc, TM1pyException)

    def test_is_not_instance_of_tm1py_rest_exception(self):
        exc = TM1pyNetworkException(
            response=GENERIC_HTML_NO_RAY_ID,
            status_code=403,
            reason="Forbidden",
            headers=SAMPLE_HEADERS,
        )
        self.assertNotIsInstance(exc, TM1pyRestException)

    def test_can_be_raised_and_caught_as_tm1py_exception(self):
        with self.assertRaises(TM1pyException):
            raise TM1pyNetworkException(
                response=GENERIC_HTML_NO_RAY_ID,
                status_code=403,
                reason="Forbidden",
                headers=SAMPLE_HEADERS,
            )

    def test_not_caught_by_tm1py_rest_exception_handler(self):
        """Existing except TM1pyRestException blocks must NOT swallow this exception."""
        caught_as_rest = False
        try:
            raise TM1pyNetworkException(
                response=GENERIC_HTML_NO_RAY_ID,
                status_code=403,
                reason="Forbidden",
                headers=SAMPLE_HEADERS,
            )
        except TM1pyRestException:
            caught_as_rest = True
        except TM1pyException:
            pass

        self.assertFalse(caught_as_rest, "TM1pyNetworkException must not be caught by TM1pyRestException handler")

    def test_verify_response_raises_network_exception_for_html(self):
        response = Response()
        response.status_code = 403
        response._content = CLOUDFLARE_HTML_WITH_RAY_ID.encode("utf-8")
        response.headers = {"Content-Type": "text/html"}
        response.reason = "Forbidden"

        with self.assertRaises(TM1pyNetworkException):
            RestService.verify_response(response)

    def test_verify_response_raises_network_exception_for_html_body_without_html_content_type(self):
        """HTML body detected via the <!DOCTYPE signature even when Content-Type is not text/html."""
        response = Response()
        response.status_code = 502
        response._content = GENERIC_HTML_NO_RAY_ID.encode("utf-8")
        response.headers = {"Content-Type": "application/octet-stream"}
        response.reason = "Bad Gateway"

        with self.assertRaises(TM1pyNetworkException):
            RestService.verify_response(response)

    def test_verify_response_raises_network_exception_for_html_content_type_without_doctype(self):
        """text/html Content-Type (with charset) detected even when the body has no <!DOCTYPE prefix."""
        response = Response()
        response.status_code = 403
        response._content = b"<html><body>blocked</body></html>"
        response.headers = {"Content-Type": "text/html; charset=utf-8"}
        response.reason = "Forbidden"

        with self.assertRaises(TM1pyNetworkException):
            RestService.verify_response(response)

    def test_verify_response_raises_rest_exception_for_json_error(self):
        """Genuine TM1 REST errors (JSON, non-HTML) must still raise TM1pyRestException."""
        response = Response()
        response.status_code = 400
        response._content = b'{"error":{"message":"Invalid MDX statement"}}'
        response.headers = {"Content-Type": "application/json"}
        response.reason = "Bad Request"

        with self.assertRaises(TM1pyRestException):
            RestService.verify_response(response)

        try:
            RestService.verify_response(response)
        except TM1pyRestException as exc:
            self.assertNotIsInstance(exc, TM1pyNetworkException)

    def test_verify_response_does_not_raise_for_ok_response(self):
        """A successful response must pass through without raising, even with an HTML-ish body."""
        response = Response()
        response.status_code = 200
        response._content = b"<!DOCTYPE html><html></html>"
        response.headers = {"Content-Type": "text/html"}
        response.reason = "OK"

        self.assertIsNone(RestService.verify_response(response))


if __name__ == "__main__":
    unittest.main()
