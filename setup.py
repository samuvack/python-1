#!/usr/bin/env python

# Stolen from Shapely's setup.py
# Two environment variables influence this script.
#
# PDAL_LIBRARY_PATH: a path to a PDAL C++ shared library.
#
# PDAL_CONFIG: the path to a pdal-config program that points to PDAL version,
# headers, and libraries.
#
# NB: within this setup scripts, software versions are evaluated according
# to https://www.python.org/dev/peps/pep-0440/.

import logging
import os
import platform
import sys
import numpy
from Cython.Build import cythonize

USE_CYTHON = True
try:
    from Cython.Build import cythonize
except ImportError:
    USE_CYTHON = False

ext = '.pyx' if USE_CYTHON else '.cpp'

from setuptools import setup
from packaging.version import Version


logging.basicConfig()
log = logging.getLogger(__file__)

# python -W all setup.py ...
if 'all' in sys.warnoptions:
    log.level = logging.DEBUG


# Second try: use PDAL_CONFIG environment variable
if 'PDAL_CONFIG' in os.environ:
    pdal_config = os.environ['PDAL_CONFIG']
    log.debug('pdal_config: %s', pdal_config)
else:
    pdal_config = 'pdal-config'
    # in case of windows...
    if os.name in ['nt']:
        pdal_config += '.bat'


def get_pdal_config(option):
    '''Get configuration option from the `pdal-config` development utility

    This code was adapted from Shapely's geos-config stuff
    '''
    import subprocess
    pdal_config = globals().get('pdal_config')
    if not pdal_config or not isinstance(pdal_config, str):
        raise OSError('Path to pdal-config is not set')
    try:
        stdout, stderr = subprocess.Popen(
            [pdal_config, option],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except OSError as ex:
        # e.g., [Errno 2] No such file or directory
        raise OSError(
            'Could not find pdal-config %r: %s' % (pdal_config, ex))
    if stderr and not stdout:
        raise ValueError(stderr.strip())
    if sys.version_info[0] >= 3:
        result = stdout.decode('ascii').strip()
    else:
        result = stdout.strip()
    log.debug('%s %s: %r', pdal_config, option, result)
    return result

# Get the version from the pdal module
module_version = None
with open('pdal/__init__.py', 'r') as fp:
    for line in fp:
        if line.startswith("__version__"):
            module_version = Version(line.split("=")[1].strip().strip("\"'"))
            break

if not module_version:
    raise ValueError("Could not determine PDAL's version")

# Handle UTF-8 encoding of certain text files.
open_kwds = {}
if sys.version_info >= (3,):
    open_kwds['encoding'] = 'utf-8'

with open('VERSION.txt', 'w', **open_kwds) as fp:
    fp.write(str(module_version))

with open('README.rst', 'r', **open_kwds) as fp:
    readme = fp.read()

with open('CHANGES.txt', 'r', **open_kwds) as fp:
    changes = fp.read()

long_description = readme + '\n\n' +  changes

include_dirs = []
library_dirs = []
libraries = []
extra_link_args = []
extra_compile_args = []

if os.name in ['nt']:
    library_dirs = ['c:/OSGeo4W64/lib']
    libraries = ['pdalcpp','pdal_plugin_reader_numpy','pdal_util','ws2_32']
    extra_compile_args = ['/DNOMINMAX',]

from setuptools.extension import Extension as DistutilsExtension

if pdal_config and "clean" not in sys.argv:
    # Collect other options from PDAL
    try:

        # Running against different major versions is going to fail.
        # Minor versions might too, depending on numpy.
        for item in get_pdal_config('--python-version').split():
            if item:
                # 2.7.4 or 3.5.2
                built_version = item.split('.')
                built_major = int(built_version[0])
                running_major = int(sys.version_info[0])
                if built_major != running_major:
                    message = "Version mismatch. PDAL Python support was compiled against version %d.x but setup is running version is %d.x. "
                    raise Exception(message % (built_major, running_major))

    # older versions of pdal-config do not include --python-version switch
    except ValueError:
        pass

    separator = ':'
    if os.name in ['nt']:
        separator = ';'

    for item in get_pdal_config('--includes').split():
        if item.startswith("-I"):
            include_dirs.extend(item[2:].split(separator))

    for item in get_pdal_config('--libs').split():
        if item.startswith("-L"):
            library_dirs.extend(item[2:].split(separator))
        elif item.startswith("-l"):
            libraries.append(item[2:])

include_dirs.append(numpy.get_include())

if os.name != 'nt':
    extra_compile_args = ['-std=c++11','-Wno-unknown-pragmas']

if platform.system() == 'Darwin':
    extra_link_args.append('-Wl,-rpath,'+library_dirs[0])

DEBUG=True
if DEBUG:
    if os.name != 'nt':
        extra_compile_args += ['-g','-O0']

libraries.append('pdal_plugin_reader_numpy')
sources=['pdal/libpdalpython'+ext, "pdal/PyPipeline.cpp"  ]
extensions = [DistutilsExtension("*",
                                   sources,
                                   include_dirs=include_dirs,
                                   library_dirs=library_dirs,
                                   extra_compile_args=extra_compile_args,
                                   libraries=libraries,
                                   extra_link_args=extra_link_args,)]
if USE_CYTHON and "clean" not in sys.argv:
    from Cython.Build import cythonize
    extensions= cythonize(extensions, language="c++")

setup_args = dict(
    name                = 'PDAL',
    version             = str(module_version),
    requires            = ['Python (>=2.7)', ],
    description         = 'Point cloud data processing',
    license             = 'BSD',
    keywords            = 'point cloud spatial',
    author              = 'Howard Butler',
    author_email        = 'howard@hobu.co',
    maintainer          = 'Howard Butler',
    maintainer_email    = 'howard@hobu.co',
    url                 = 'http://pdal.io',
    long_description    = long_description,
    test_suite          = 'test',
    packages            = [
        'pdal',
    ],
    classifiers         = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS',
    ],
    cmdclass           = {},
    install_requires   = ['numpy', 'packaging'],
)
setup(ext_modules=extensions, **setup_args)

