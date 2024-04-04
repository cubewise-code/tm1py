# Setup TM1py Tests

- `pip install pytest`

- Use a TM1 development environment

- Specify your instance coordinates in the config.ini file as `tm1srv01`

- `EnableSandboxDimension` config parameter must be set to `F` for the target TM1 instance

# Run TM1py Tests

## Run tests via commandline 

### To run all tests

On Windows:

`pytest .\Tests\`

On Linux and macOS:

`pytest ./Tests/`

### To run a specific test file from the `Tests` folder

On Windows:

`pytest .\Tests\ChoreService_test.py`

On Linux and macOS:

`pytest ./Tests/ChoreService_test.py`

## Run tests via PyCharm

### To run all tests

rightclick `Tests` folder -> run 'pytest in Tests'

## To run a specific test file from the `Tests` folder:
rightclick file (e.g., `ChoreService_test.py`) -> run 'pytest in ChoreService_test.py'
