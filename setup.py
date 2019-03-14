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

dynamic_options = {}
version = None

# Deduce version, if possible.
if os.path.isfile('../VERSION'):
    version = read('../VERSION')
else:
    dynamic_options['version_format'] = '{tag}.dev{commitcount}+git.{gitsha}'
    dynamic_options['setup_requires'] = ['setuptools-git-version']

setup(
    name='Facedancer',
    version=version,
    url='https://greatscottgadgets.com/greatfet/',
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
    **dynamic_options
)
