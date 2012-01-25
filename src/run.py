#!/usr/bin/env python
"""Minimal run script.

This script is just a convenient method for running Cake if it has not been
installed to your Python directory via 'python setup.py install'. If Cake
has been installed it can instead be run by simply typing 'cake'.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

if __name__ == '__main__':
  """Main entrypoint.
  """
  import cake.main
  cake.main.execute()
