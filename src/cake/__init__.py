import threading
import sys

builders = threading.local()
sys.modules['cake.builders'] = builders
