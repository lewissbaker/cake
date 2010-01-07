import os.path
import time
import threading

from cake.tools.compilers.dummy import DummyCompiler
from cake.tools.script import ScriptTool
from cake.tools.filesys import FileSystemTool
from cake.engine import Engine, Variant

engine = Engine()
variant = Variant(name="debug")
variant.tools["compiler"] = DummyCompiler()
variant.tools["script"] = ScriptTool()
variant.tools["filesys"] = FileSystemTool()
engine.addVariant(variant, default=True)

scriptPath = os.path.join(os.path.dirname(__file__), "source.cake")
t = engine.execute(scriptPath)

sem = threading.Semaphore(0)
t.addCallback(sem.release)
sem.acquire()
