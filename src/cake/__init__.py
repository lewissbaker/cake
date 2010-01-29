import threading
import sys

builders = threading.local()
sys.modules['cake.builders'] = builders

__version_info__ = (0, 1)
__version__ = '.'.join(str(v) for v in __version_info__)
