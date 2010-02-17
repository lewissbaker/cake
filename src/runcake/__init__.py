"""Minimal bootstrapping module.
"""

def run():
  try:
    import cake.main
    return cake.main.run()
  except KeyboardInterrupt:
    import sys
    sys.exit(-1)