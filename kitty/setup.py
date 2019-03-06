from setuptools import setup, find_packages
import os
import sys


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = '0.7.1'
AUTHOR = 'Cisco SAS team'
EMAIL = 'kitty-fuzzer@googlegroups.com'
URL = 'https://github.com/cisco-sas/kitty.git'
DESCRIPTION = read('README.rst')
KEYWORDS = 'fuzz,fuzzing,framework,sulley,kitty,kittyfuzzer,security'

setup(
        name='kittyfuzzer',
        version=VERSION,
        description='Kitty fuzzing framework',
        long_description=DESCRIPTION,
        author=AUTHOR,
        author_email=EMAIL,
        url=URL,
        packages=find_packages(),
        install_requires=['docopt', 'bitstring', 'six', 'requests'],
        keywords=KEYWORDS,
        entry_points={
            'console_scripts': [
                'kitty-web-client=kitty.bin.kitty_web_client:_main',
                'kitty-template-tester=kitty.bin.kitty_template_tester:_main',
                'kitty-tool=kitty.bin.kitty_tool:_main',
            ]
        },
        package_data={'kitty': ['interfaces/web/static/*']}
)
