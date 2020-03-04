import os
import sys
from setuptools import setup, find_packages

def read(fname):
    filename = os.path.join(os.path.dirname(__file__), fname)
    with open(filename, 'r') as f:
        return f.read()

# Ensure we're not accidentally installed on Python2.
if sys.version_info.major < 3:
    raise RuntimeError("Facedancer is not compatible with python2; and requires python 3.0 or later.")


setup_req=[]
setup_options = {}

# Deduce version, if possible.
if os.path.isfile('VERSION'):
    setup_options['version'] = read('VERSION')
else:
    setup_options['version_config'] =  {
        "version_format": '{tag}.dev+git.{sha}',
        "starting_version": "v2.9"
    }
    setup_req.append('even-better-setuptools-git-version')

setup(
    name='facedancer',
    setup_requires=setup_req,

    url='https://github.com/usb-tools/facedancer',
    author = "Kate Temkin",
    author_email = "kate@ktemkin.com",

    license='BSD',
    tests_require=[''],
    install_requires=['pyusb'],
    description='Python library for emulating USB devices',
    long_description=read('README.md'),
    packages=find_packages(),
    include_package_data=True,
    platforms='any',

    classifiers = [
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Environment :: Console',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering',
        'Topic :: Security',
        'Programming Language :: Python',
        "Programming Language :: Python :: 3",
        ],
    extras_require={},
    **setup_options
)
