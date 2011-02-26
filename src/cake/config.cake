#-------------------------------------------------------------------------------
# Default configuration used if none is passed passed on the command line or
# found by searching up from the working directory.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.logging import LoggingTool
from cake.library.variant import VariantTool
from cake.library.shell import ShellTool
from cake.library.filesys import FileSystemTool
from cake.library.zipping import ZipTool
from cake.library.compilers import CompilerNotFoundError
from cake.library.compilers.dummy import DummyCompiler
import cake.system

hostPlatform = cake.system.platform().lower()
hostArchitecture = cake.system.architecture().lower()

configuration = Script.getCurrent().configuration

variant = Variant(platform=hostPlatform, architecture=hostArchitecture)
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["logging"] = LoggingTool(configuration=configuration)
variant.tools["variant"] = VariantTool(configuration=configuration)
variant.tools["shell"] = ShellTool(configuration=configuration)
variant.tools["filesys"] = FileSystemTool(configuration=configuration)
variant.tools["zipping"] = ZipTool(configuration=configuration)
variant.tools["dummy"] = DummyCompiler(configuration=configuration)
variant.tools["compiler"] = variant.tools["dummy"]
# GCC Compiler
try:
  from cake.library.compilers.gcc import findGccCompiler
  gcc = variant.tools["gcc"] = findGccCompiler(configuration=configuration)
  variant.tools["compiler"] = gcc
  gcc.addLibrary("stdc++")
except CompilerNotFoundError:
  pass
if cake.system.isWindows():
  # MSVC Compiler
  try:
    from cake.library.compilers.gcc import findMinGWCompiler
    mingw = findMinGWCompiler(configuration=configuration)
    variant.tools["compiler"] = mingw
  except CompilerNotFoundError:
    pass
  # MinGW Compiler
  try:
    from cake.library.compilers.msvc import findMsvcCompiler
    msvc = findMsvcCompiler(configuration=configuration)
    msvc.addDefine("WIN32")
    if msvc.architecture in ["x64", "ia64"]:
      msvc.addDefine("WIN64")
    if msvc.architecture != hostArchitecture:
      variant = variant.clone(architecture=msvc.architecture)
    variant.tools["msvc"] = msvc
    variant.tools["compiler"] = msvc
  except CompilerNotFoundError:
    pass
configuration.addVariant(variant)
