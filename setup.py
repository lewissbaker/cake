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
  versionFilePath = os.path.join(os.path.dirname(__file__), 'src', 'cake', 'version.py')
  cakevars = {}
  if sys.hexversion >= 0x03000000:
    exec(compile(open(versionFilePath).read(), versionFilePath, 'exec'), {}, cakevars)
  else:
    execfile(versionFilePath, {}, cakevars)
  
  from setuptools import setup, find_packages
  
  # Should we use Python 3.x support?
  extra = {}
  if sys.hexversion >= 0x03000000:
    extra['use_2to3'] = True
  
  setup(
    name='Cake',
    version=cakevars["__version__"],
    author="Lewis Baker, Stuart McMahon.",
    author_email='lewisbaker@users.sourceforge.net, stuartmcmahon@users.sourceforge.net',
    url="http://sourceforge.net/projects/cake-build",
    description="A build system written in Python.",
    license="MIT",
    scripts=['src/cakemain.py'],#, 'win32/executable/Release/cake.exe'],
    package_dir={'cake' : 'src/cake'},
    package_data={'cake' : ['config.cake']},
    packages=find_packages('src', exclude=['*.test', '*.test.*']),
    entry_points={
      'console_scripts': [
        'cake = cakemain:run',
        ],
      },
    **extra
    )
  return 0

if __name__ == "__main__":
  sys.exit(run())
