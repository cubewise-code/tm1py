import functools

def skip_if_no_pandas(func):

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            import pandas
            return func(self, *args, **kwargs)
        except:
            self.skipTest(f"Test '{func.__name__}' requires pandas")

    return wrapper