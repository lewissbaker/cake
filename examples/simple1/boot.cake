import os.path
import time

from cake.tools.compilers import dummy
from cake.engine import Engine, Variant

engine = Engine()
variant = Variant(name="debug")
variant.tools["compiler"] = dummy.DummyCompiler()
engine.addVariant(variant, default=True)

scriptPath = os.path.join(os.path.dirname(__file__), "source.cake")
t = engine.execute(scriptPath)

while not t.completed:
  time.sleep()
