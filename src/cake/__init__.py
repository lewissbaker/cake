import threading
import sys

# Note: Use semantic versioning (http://semver.org) when changing version.
__version_info__ = (0, 1, 0)
__version__ = '.'.join(str(v) for v in __version_info__)

# We want the 'cake.builders' module to have thread-local contents so that
# Cake scripts can get access to their builders using standard python import
# statements. 
builders = threading.local()
sys.modules['cake.builders'] = builders

