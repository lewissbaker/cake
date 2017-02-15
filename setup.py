"""Setup script.

This script is used for installation and generation of
redistributable packages.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys

def run():
  from distribute_setup import use_setuptools
  use_setuptools()
  
  # Grab the __version__ defined in version.py
  import os.path
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
  import cake.version
  
  from setuptools import setup, find_packages
  setup(
    name='Cake',
    version=cake.version.__version__,
    author="Lewis Baker, Stuart McMahon.",
    author_email='lewisbaker@users.sourceforge.net, stuartmcmahon@users.sourceforge.net',
    url="http://sourceforge.net/projects/cake-build",
    description="A build system written in Python.",
    license="MIT",
    package_dir={'cake' : 'src/cake'},
    packages=find_packages('src', exclude=['*.test', '*.test.*']),
    entry_points={
      'console_scripts': [
        'cake = cake.main:execute',
        ],
      },
    test_suite='cake.test',
    use_2to3=sys.hexversion >= 0x03000000, # Use Python 3.x support?
    )
  return 0

if __name__ == "__main__":
  sys.exit(run())
