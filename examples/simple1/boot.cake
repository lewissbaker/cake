import os.path
import time

from cake.tools.compilers.dummy import DummyCompiler
from cake.tools.script import ScriptBuilder
from cake.engine import Engine, Variant

engine = Engine()
variant = Variant(name="debug")
variant.tools["compiler"] = DummyCompiler()
variant.tools["script"] = ScriptBuilder()
engine.addVariant(variant, default=True)

scriptPath = os.path.join(os.path.dirname(__file__), "source.cake")
t = engine.execute(scriptPath)

while not t.completed:
  time.sleep()
