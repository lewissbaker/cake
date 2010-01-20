import os
import cake.path
from cake.tools.compilers.dummy import DummyCompiler
from cake.tools.compilers.msvc import MsvcCompiler
from cake.tools.script import ScriptTool
from cake.tools.filesys import FileSystemTool
from cake.tools.env import Environment
from cake.engine import Variant

base = Variant(name="base")
base.tools["script"] = ScriptTool()
base.tools["filesys"] = FileSystemTool()
env = base.tools["env"] = Environment()
env["ROOT"] = cake.path.directory(__file__)
env["BUILD"] = "${ROOT}/build/${PLATFORM}_${COMPILER}_${RELEASE}"

programFiles = os.environ['PROGRAMFILES']
msvsInstall = cake.path.join(programFiles, "Microsoft Visual Studio 8") 

windows = base.clone(name="windows")
compiler = windows.tools["compiler"] = MsvcCompiler(
  clExe=cake.path.join(msvsInstall, r"VC\bin\cl.exe"),
  libExe=cake.path.join(msvsInstall, r"VC\bin\lib.exe"),
  linkExe=cake.path.join(msvsInstall, r"VC\bin\link.exe"),
  dllPaths=[cake.path.join(msvsInstall, r"Common7\IDE")],
  )
compiler.addIncludePath(
  cake.path.join(msvsInstall, r"VC\include"),
  )
compiler.addLibraryPath(
  cake.path.join(msvsInstall, r"VC\lib")
  )
compiler.addLibraryPath(
  cake.path.join(msvsInstall, r"VC\PlatformSDK\Lib"),
  )
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

windowsOptimised = windows.clone("win32-opt")
compiler = windowsOptimised.tools["compiler"]
compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
env = windowsOptimised.tools["env"]
env["RELEASE"] = "optimised"
engine.addVariant(windowsOptimised)
