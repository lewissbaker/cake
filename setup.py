"""Setup script.

This script is used for installation and generation of
redistributable packages.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license (see license.txt).
"""

import sys

def run():
  import ez_setup
  ez_setup.use_setuptools()
  
  import os.path
  sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

  import cake
  from setuptools import setup, find_packages
  setup(
    name='Cake',
    version=cake.__version__,
    author="Lewis Baker, Stuart McMahon.",
    url="http://sourceforge.net/projects/cake-build",
    description="A build system written in Python.",
    license="MIT",
    py_modules=['cakemain'],
    package_dir={'' : 'src'},
    packages=find_packages('src', exclude=['*.test', '*.test.*']),
    entry_points={
      'console_scripts': [
        'cake = cakemain:run',
        ],
      }
    )
  return 0

if __name__ == "__main__":
  sys.exit(run())