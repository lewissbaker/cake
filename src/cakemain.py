"""Minimal main entrypoint.

This main module reduces the risk of a stack dump caused by
a KeyboardIntterupt by not loading any modules until a
try-except block is in place.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license (see license.txt).
"""

def run():
  """Minimal run function.
  """
  try:
    import sys
    import cake.runner
    sys.exit(cake.runner.run())
  except KeyboardInterrupt:
    import sys
    sys.exit(-1)

if __name__ == '__main__':
  """Minimal main function.
  """
  run()