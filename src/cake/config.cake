#-------------------------------------------------------------------------------
# Default configuration used if none is passed on the command line or
# found by searching up from the working directory.
#-------------------------------------------------------------------------------
from cake.engine import Variant
from cake.library.env import EnvironmentTool
from cake.library.script import ScriptTool
from cake.library.logging import LoggingTool
from cake.library.variant import VariantTool
from cake.library.shell import ShellTool
from cake.library.filesys import FileSystemTool
from cake.library.zipping import ZipTool
from cake.library.compilers import CompilerNotFoundError
from cake.library.compilers.dummy import DummyCompiler
from cake.library import waitForAsyncResult
from cake.script import Script

import cake.system
import cake.path

platform = cake.system.platform().lower()
hostArchitecture = cake.system.architecture().lower()
configuration = Script.getCurrent().configuration

# Override the configuration basePath() function.
def basePath(value):
  from cake.tools import script, env

  @waitForAsyncResult
  def _basePath(path):
    if isinstance(path, basestring):
      path = env.expand(path)
      if path.startswith("#"):
        if path[1] in '\\/': # Keep project paths relative but remove slashes.
          return path[2:]
        else:
          return path[1:]
      elif cake.path.isAbs(path):
        return path # Keep absolute paths as found.
      else:
        return script.cwd(path) # Prefix relative paths with scripts dir.
    elif isinstance(path, (list, set)): # Convert set->list in case of valid duplicates.
      return list(_basePath(p) for p in path)
    elif isinstance(path, tuple):
      return tuple(_basePath(p) for p in path)
    elif isinstance(path, dict):
      return dict((k, _basePath(v)) for k, v in path.iteritems())
    else:
      return path # Could be a FileTarget. Leave it as is.
  
  return _basePath(value)
      
configuration.basePath = basePath

def createVariant(platform, architecture, compiler):
  env = EnvironmentTool(configuration=configuration)
  if architecture:
    env["TARGET"] = "-".join([platform, compiler.name, architecture])
  else:
    env["TARGET"] = "-".join([platform, compiler.name])
  
  variant = Variant(platform=platform, architecture=architecture, compiler=compiler.name)
  variant.tools["env"] = env
  variant.tools["script"] = ScriptTool(configuration=configuration)
  variant.tools["logging"] = LoggingTool(configuration=configuration)
  variant.tools["variant"] = VariantTool(configuration=configuration)
  variant.tools["shell"] = ShellTool(configuration=configuration)
  variant.tools["filesys"] = FileSystemTool(configuration=configuration)
  variant.tools["zipping"] = ZipTool(configuration=configuration)
  variant.tools["compiler"] = compiler
  configuration.addVariant(variant)

# Create Dummy Compiler.
compiler = DummyCompiler(configuration=configuration)
createVariant(platform, "", compiler)

# Create GCC Compiler.
try:
  from cake.library.compilers.gcc import findGccCompiler
  compiler = findGccCompiler(configuration=configuration)
  compiler.addLibrary("stdc++")
  createVariant(platform, hostArchitecture, compiler)
except CompilerNotFoundError:
  pass

if cake.system.isWindows():
  # Create MinGW Compiler.
  try:
    from cake.library.compilers.gcc import findMinGWCompiler
    compiler = findMinGWCompiler(configuration=configuration)
    createVariant(platform, hostArchitecture, compiler)
  except CompilerNotFoundError:
    pass
  # Create MSVC Compilers.
  try:
    from cake.library.compilers.msvc import findMsvcCompiler
    for architecture in ["x86", "amd64", "ia64"]:
      compiler = findMsvcCompiler(configuration=configuration, architecture=architecture)
      compiler.addDefine("WIN32")
      if architecture in ["amd64", "ia64"]:
        compiler.addDefine("WIN64")
      createVariant(platform, architecture, compiler)
  except CompilerNotFoundError:
    pass

