from setuptools import setup

SCHEDULE_VERSION = '1.4.1'
SCHEDULE_DOWNLOAD_URL = (
        'https://github.com/Cubewise-code/TM1py/tarball/' + SCHEDULE_VERSION
)

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='TM1py',
    packages=['TM1py', 'TM1py/Exceptions', 'TM1py/Objects', 'TM1py/Services', 'TM1py/Utils'],
    version=SCHEDULE_VERSION,
    description='A python module for TM1.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='MIT',
    author='Marius Wirtz',
    author_email='MWirtz@cubewise.com',
    url='https://github.com/cubewise-code/tm1py',
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
        'Programming Language :: Python :: 3.7',
        'Natural Language :: English',
    ],
    install_requires=[
        'requests',
        'pandas',
        'pytz',
        'requests_negotiate_sspi;platform_system=="Windows"'],
    python_requires='>=3.5',
)
