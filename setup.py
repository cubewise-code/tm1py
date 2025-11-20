from setuptools import setup

# All configuration is now in pyproject.toml
# This setup.py is kept for backwards compatibility
setup(
    packages=["TM1py", "TM1py/Exceptions", "TM1py/Objects", "TM1py/Services", "TM1py/Utils"],
)
