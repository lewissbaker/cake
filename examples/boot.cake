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

#
# Dummy
#
dummy = base.clone(platform="unknown", compiler="dummy")
dummy.tools["compiler"] = DummyCompiler()

env = dummy.tools["env"]
env["PLATFORM"] = "unknown"
env["COMPILER"] = "dummy"

#
# Dummy Debug
#
dummyDebug = dummy.clone(release="debug")
compiler = dummyDebug.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.NO_OPTIMISATION
env = dummyDebug.tools["env"]
env["RELEASE"] = "debug"
engine.addVariant(dummyDebug, default=True)

#
# Dummy Optimised
#
dummyOptimised = dummy.clone(release="optimised")
compiler = dummyOptimised.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
env = dummyOptimised.tools["env"]
env["RELEASE"] = "optimised"
engine.addVariant(dummyOptimised)

#
# Windows
#
windows = base.clone(platform="windows", compiler="msvc")
windows.tools["compiler"] = findMsvcCompiler() 

env = windows.tools["env"]
env["PLATFORM"] = "windows"
env["COMPILER"] = "msvc"

#
# Window Debug
#
windowsDebug = windows.clone(release="debug")
compiler = windowsDebug.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.NO_OPTIMISATION
env = windowsDebug.tools["env"]
env["RELEASE"] = "debug"
engine.addVariant(windowsDebug)

#
# Windows Optimised
#
windowsOptimised = windows.clone(release="optimised")
compiler = windowsOptimised.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
env = windowsOptimised.tools["env"]
env["RELEASE"] = "optimised"
engine.addVariant(windowsOptimised)
