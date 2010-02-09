import cake.path
from cake.library.compilers.dummy import DummyCompiler
from cake.library.compilers.msvc import findCompiler as findMsvcCompiler
from cake.library.script import ScriptTool
from cake.library.filesys import FileSystemTool
from cake.library.env import Environment
from cake.engine import Variant

base = Variant()
base.tools["script"] = ScriptTool()
base.tools["filesys"] = FileSystemTool()
env = base.tools["env"] = Environment()
env["BUILD"] = "build/${PLATFORM}_${COMPILER}_${RELEASE}"

windows = base.clone()
compiler = windows.tools["compiler"] = findMsvcCompiler() 

env = windows.tools["env"]
env["PLATFORM"] = "windows"
env["COMPILER"] = "msvc"

windowsDebug = windows.clone(name="win32-debug")
compiler = windowsDebug.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.NO_OPTIMISATION
env = windowsDebug.tools["env"]
env["RELEASE"] = "debug"
engine.addVariant(windowsDebug, default=True)

windowsOptimised = windows.clone(name="win32-opt")
compiler = windowsOptimised.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
env = windowsOptimised.tools["env"]
env["RELEASE"] = "optimised"
engine.addVariant(windowsOptimised)
