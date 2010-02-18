"""Minimal main entrypoint.

This main module reduces the risk of a stack dump caused by
a KeyboardIntterupt by not loading any modules until a
try-except block is in place.  
"""

def run():
  """Minimal run function.
  """
  try:
    import sys
    import cake.main
    sys.exit(cake.main.run())
  except KeyboardInterrupt:
    import sys
    sys.exit(-1)

if __name__ == '__main__':
  """Minimal main function.
  """
  run()