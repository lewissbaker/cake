import threading

import cake.path
from cake.tools.compilers.dummy import DummyCompiler
from cake.tools.script import ScriptTool
from cake.tools.filesys import FileSystemTool
from cake.tools.env import Environment
from cake.engine import Engine, Variant

engine = Engine()

base = Variant(name="base")
base.tools["script"] = ScriptTool()
base.tools["filesys"] = FileSystemTool()
env = base.tools["env"] = Environment()
env["BUILD"] = "build/${PLATFORM}_${COMPILER}_${RELEASE}"

windows = base.clone(name="windows")
windows.tools["compiler"] = DummyCompiler()
env = windows.tools["env"]
env["PLATFORM"] = "windows"
env["COMPILER"] = "dummy"

windowsDebug = windows.clone(name="win32-debug")
compiler = windowsDebug.tools["compiler"]
compiler.useDebugSymbols = True
compiler.optimisation = compiler.NO_OPTIMISATION
env = windowsDebug.tools["env"]
env["RELEASE"] = "debug"
engine.addVariant(windowsDebug, default=True)

windowsOptimised = windows.clone("win32-opt")
compiler = windowsOptimised.tools["compiler"]
compiler.useDebugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
env = windowsOptimised.tools["env"]
env["RELEASE"] = "optimised"
engine.addVariant(windowsOptimised)

scriptPath = cake.path.join(cake.path.directory(__file__), "source.cake")
t = engine.execute(scriptPath)

sem = threading.Semaphore(0)
t.addCallback(sem.release)
sem.acquire()

if t.succeeded:
  print "Build succeeded"
else:
  print "Build failed"
