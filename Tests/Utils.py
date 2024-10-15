import functools

from TM1py.Utils.Utils import verify_version


def skip_if_no_pandas(func):
    """ 
    Checks whether pandas is installed and skips the test if not
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            import pandas

            return func(self, *args, **kwargs)
        except ImportError:
            return self.skipTest(f"Test '{func.__name__}' requires pandas")

    return wrapper


def skip_if_version_lower_than(version):
    """ 
    Checks whether TM1 version is lower than a certain version and skips the test 
    if this is the case. This function is useful if a test needs a minimum required version.
    """

    def wrap(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if not verify_version(required_version=version, version=self.tm1.version):
                return self.skipTest(
                    f"Function '{func.__name__,}' requires TM1 server version >= '{version}'"
                )
            else:
                return func(self, *args, **kwargs)

        return wrapper

    return wrap


def skip_if_version_higher_or_equal_than(version):
    """
    Checks whether TM1 version is higher or equal than a certain version and skips the test 
    if this is the case. This function is useful if a test should not run for higher versions.
    """

    def wrap(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            if verify_version(required_version=version, version=self.tm1.version):
                return self.skipTest(
                    f"Function '{func.__name__,}' requires TM1 server version < '{version}'"
                )
            else:
                return func(self, *args, **kwargs)

        return wrapper

    return wrap
