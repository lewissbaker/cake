"""Main entrypoint.

This main module reduces the risk of a stack dump caused by a
KeyboardInterrupt by not loading any unnecessary modules until a
keyboard interrupt signal handler is in place.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

def execute():
  """Execute Cake passing the result to sys.exit().
  """
  import signal
  import sys

  def signalHandler(signum, frame):
    sys.exit(-1)
  signal.signal(signal.SIGINT, signalHandler)
  
  import cake.runner
  sys.exit(cake.runner.run())

if __name__ == '__main__':
  """Main entrypoint.
  """
  execute()
