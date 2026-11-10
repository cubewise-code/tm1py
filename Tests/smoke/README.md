# TM1py Smoke Tests

## Purpose

Smoke tests are fast, deterministic checks of TM1py's core functionality.
They **do not need a TM1 server**: every HTTP call to the TM1 REST API is
intercepted and answered by mocked responses (using the
[`responses`](https://github.com/getsentry/responses) library).

They run automatically on every pull request (see
`.github/workflows/pr-validation.yml`) to give quick feedback and catch
breaking changes early. They complement, but do not replace, the integration
tests in the `Tests` folder, which run against a real TM1 instance.

## Requirements

```bash
pip install -e ".[dev]"
```

No `config.ini` and no TM1 instance are required.

## Running the tests

Run all smoke tests from the repository root:

```bash
pytest Tests/smoke
```

Run a single file or test:

```bash
pytest Tests/smoke/ConnectionSmoke_test.py
pytest Tests/smoke/ConnectionSmoke_test.py::TestConnectionSmoke::test_is_connected
```

## How it works

`SmokeTestBase` is the base class for all smoke tests. For each test it:

1. starts a `responses.RequestsMock` (available as `self.rsps`),
2. mocks `GET /Configuration/ProductVersion/$value`, which `TM1Service` calls on construction,
3. creates a `TM1Service` instance (available as `self.tm1`) against the fake server `https://tm1server:8000/api/v1`
   (available as `self.base_url`).

The mock is created with `assert_all_requests_are_fired=True`: a test fails if
a mocked endpoint is never called, and any unmocked request raises a
`ConnectionError`. This keeps the mocks and the code under test in sync.

Helpers:

| Helper                               | Purpose                                            |
|--------------------------------------|----------------------------------------------------|
| `mock_server_name(name)`             | Mocks `GET /Configuration/ServerName/$value`       |
| `mock_get(path, body, status=200)`   | Mocks any `GET` endpoint with a raw body           |
| `mock_bootstrap_version(version)`    | Mocks the product version (called in `setUp`)      |

To simulate another TM1 version, override `mocked_server_version` in your test
class. To change the connection parameters, override `get_tm1_kwargs()`.

## Adding a smoke test

1. Create a file named `<Area>Smoke_test.py` in this folder.
2. Subclass `SmokeTestBase`.
3. Mock every REST call the tested method makes, then call the method and assert on the result.

Example:

```python
import responses

from .SmokeTestBase import SmokeTestBase


class TestCubeSmoke(SmokeTestBase):

    def test_get_all_cube_names(self):
        self.rsps.add(
            responses.GET,
            f"{self.base_url}/Cubes?$select=Name",
            json={"value": [{"Name": "Sales"}, {"Name": "Plan"}]},
            status=200,
        )

        names = self.tm1.cubes.get_all_names()

        self.assertEqual(names, ["Sales", "Plan"])
```

Guidelines:

- Keep tests fast and independent: no real network access, no shared state between tests.
- Cover the happy path of commonly used functionality; edge cases belong in unit or integration tests.
- Use realistic payloads. Copying a real TM1 REST API response is the easiest way to get one.
