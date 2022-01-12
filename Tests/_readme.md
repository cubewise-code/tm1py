# Setup TM1py Tests

- `pip install pytest`

- Use a TM1 development environment

- Specify your instance coordinates in the config.ini file as `tm1srv01`

- `EnableSandboxDimension` config parameter must be set to `F` for the target TM1 instance

# Run TM1py Tests

## To run all tests with PyCharm:

rightclick `Tests` folder -> run 'pytest in Tests'

## To run tests in a given file in the `Tests` folder:
rightclick file (e.g., `ChoreService_test.py`) -> run 'pytest in ChoreService_test.py'
