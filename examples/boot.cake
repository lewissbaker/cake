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

windows = base.clone(type="code", platform="windows")
compiler = windows.tools["compiler"] = findMsvcCompiler() 

env = windows.tools["env"]
env["PLATFORM"] = "windows"
env["COMPILER"] = "msvc"

windowsDebug = windows.clone(release="debug")
compiler = windowsDebug.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.NO_OPTIMISATION
env = windowsDebug.tools["env"]
env["RELEASE"] = "debug"
engine.addVariant(windowsDebug, default=True)

windowsOptimised = windows.clone(release="optimised")
compiler = windowsOptimised.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
env = windowsOptimised.tools["env"]
env["RELEASE"] = "optimised"
engine.addVariant(windowsOptimised)

art = base.clone(type="art", platform="windows")

artDisc = art.clone(mode="disc")
engine.addVariant(artDisc)
artDev = art.clone(mode="dev")
engine.addVariant(artDev)
