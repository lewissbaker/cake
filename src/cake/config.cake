#-------------------------------------------------------------------------------
# Default configuration used if none is passed on the command line or
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

platform = cake.system.platform().lower()
architecture = cake.system.architecture().lower()

configuration = Script.getCurrent().configuration

# Dummy Compiler is the default compiler
compiler = DummyCompiler(configuration=configuration)

# Prefer GCC Compiler over previous compilers
try:
  from cake.library.compilers.gcc import findGccCompiler
  compiler = findGccCompiler(configuration=configuration)
  compiler.addLibrary("stdc++")
except CompilerNotFoundError:
  pass

if cake.system.isWindows():
  # Prefer MinGW Compiler over previous compilers
  try:
    from cake.library.compilers.gcc import findMinGWCompiler
    compiler = findMinGWCompiler(configuration=configuration)
  except CompilerNotFoundError:
    pass
  # Prefer MSVC Compiler over previous compilers
  try:
    from cake.library.compilers.msvc import findMsvcCompiler
    compiler = findMsvcCompiler(configuration=configuration)
    compiler.addDefine("WIN32")
    if compiler.architecture in ["x64", "ia64"]:
      compiler.addDefine("WIN64")
    # Get the compilers architecture in case we only have eg. an
    # x64 MSVC compiler installed on an x86 machine
    architecture = compiler.architecture
  except CompilerNotFoundError:
    pass

variant = Variant(platform=platform, architecture=architecture, compiler=compiler.name)
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["logging"] = LoggingTool(configuration=configuration)
variant.tools["variant"] = VariantTool(configuration=configuration)
variant.tools["shell"] = ShellTool(configuration=configuration)
variant.tools["filesys"] = FileSystemTool(configuration=configuration)
variant.tools["zipping"] = ZipTool(configuration=configuration)
variant.tools["compiler"] = compiler
configuration.addVariant(variant)
