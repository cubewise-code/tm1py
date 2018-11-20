import codecs

from setuptools import setup

SCHEDULE_VERSION = '1.1.0'
SCHEDULE_DOWNLOAD_URL = (
        'https://github.com/Cubewise-code/TM1py/tarball/' + SCHEDULE_VERSION
)


def read_file(filename):
    """
    Read a utf8 encoded text file and return its contents.
    """
    with codecs.open(filename, 'r', 'utf8') as f:
        return f.read()


setup(
    name='TM1py',
    packages=['TM1py', 'TM1py/Exceptions', 'TM1py/Objects', 'TM1py/Services', 'TM1py/Utils'],
    version=SCHEDULE_VERSION,
    description='A python module for TM1.',
    long_description=read_file('README.rst'),
    license='MIT',
    author='Marius Wirtz',
    author_email='MWirtz@cubewise.com',
    url='https://github.com/cubewise-code/TM1py',
    download_url=SCHEDULE_DOWNLOAD_URL,
    keywords=[
        'TM1', 'IBM Cognos TM1', 'Planning Analytics', 'PA', 'Cognos'
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Natural Language :: English',
    ],
    install_requires=['requests', 'pandas', 'dateutil'],
    python_requires='>=3.5',
)
