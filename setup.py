import os
from setuptools import setup, find_packages

def read(fname):
    filename = os.path.join(os.path.dirname(__file__), fname)
    with open(filename, 'r') as f:
        return f.read()

setup(
    name='Facedancer',
    version='2.0',
    url='https://greatscottgadgets.com/greatfet/',
    license='BSD',
    scripts=['greatfet_firmware','greatfet_info'],
    tests_require=[''],
    install_requires=['pyusb'],
    description='Python library for emulating USB devices',
    long_description=read('../README.md'),
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
    classifiers = [
        'Programming Language :: Python',
        'Development Status :: 1 - Planning',
        'Natural Language :: English',
        'Environment :: Console',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering',
        'Topic :: Security',
        ],
    extras_require={}
)
