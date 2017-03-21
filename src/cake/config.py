#-------------------------------------------------------------------------------
# Default configuration used if none is passed on the command line or
# found by searching up from the working directory.
#-------------------------------------------------------------------------------
from cake.engine import Variant
from cake.async import waitForAsyncResult
from cake.library.compilers import CompilerNotFoundError
from cake.library.compilers.dummy import DummyCompiler
from cake.library.env import EnvironmentTool
from cake.library.filesys import FileSystemTool
from cake.library.logging import LoggingTool
from cake.library.project import ProjectTool
from cake.library.script import ScriptTool
from cake.library.shell import ShellTool
from cake.library.variant import VariantTool
from cake.library.zipping import ZipTool
from cake.script import Script

import cake.path
import cake.system

platform = cake.system.platform().lower()
hostArchitecture = cake.system.architecture().lower()
configuration = Script.getCurrent().configuration
engine = Script.getCurrent().engine

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

# Create the project tool, only enabled during project generation.
projectTool = ProjectTool(configuration=configuration)
projectTool.product = ProjectTool.VS2010 # Build projects for VS2010.
projectTool.enabled = hasattr(engine.options, "createProjects") and engine.options.createProjects

# Add a build success callback that will do the actual project generation.
engine.addBuildSuccessCallback(projectTool.build)

def createVariants(platform, architecture, compiler):
  for target in ["debug", "release"]:
    variant = Variant(
      platform=platform,
      architecture=architecture,
      compiler=compiler.name,
      target=target,
      )
    variant.tools["env"] = env = EnvironmentTool(configuration=configuration)
    variant.tools["script"] = ScriptTool(configuration=configuration)
    variant.tools["logging"] = LoggingTool(configuration=configuration)
    variant.tools["variant"] = VariantTool(configuration=configuration)
    variant.tools["shell"] = ShellTool(configuration=configuration)
    variant.tools["filesys"] = FileSystemTool(configuration=configuration)
    variant.tools["zipping"] = ZipTool(configuration=configuration)
    variant.tools["compiler"] = compilerClone = compiler.clone()
    variant.tools["project"] = projectClone = projectTool.clone()

    # Set a build directory specific to this variant.
    env["VARIANT"] = "-".join([platform, compiler.name, architecture, target])
    
    # Turn on debug symbols for the debug target.
    compilerClone.debugSymbols = target == "debug"
  
    # Set the project config and platform names for this variant. Note that if
    # these are not set a default will be used that is based on the variants
    # keywords.
    projectClone.projectConfigName = '%s %s (%s) %s' % (
      platform.capitalize(),
      compiler.name.capitalize(),
      architecture,
      target.capitalize(),
      )
    projectClone.solutionConfigName = target.capitalize()
    projectClone.solutionPlatformName = '%s %s (%s)' % (
      platform.capitalize(),
      compiler.name.capitalize(),
      architecture,
      )  
    
    # Disable all other tools if the project tool is enabled.
    if projectTool.enabled:
      for tool in variant.tools.itervalues():
        if not isinstance(tool, ProjectTool):
          tool.enabled = False
              
    configuration.addVariant(variant)

# Create Dummy Compiler.
compiler = DummyCompiler(configuration=configuration)
createVariants(platform, "none", compiler)

# Create GCC Compiler.
try:
  from cake.library.compilers.gcc import findGccCompiler
  compiler = findGccCompiler(configuration=configuration)
  compiler.addLibrary("stdc++")
  createVariants(platform, hostArchitecture, compiler)
except CompilerNotFoundError:
  pass

if cake.system.isWindows():
  # Create MinGW Compiler.
  try:
    from cake.library.compilers.gcc import findMinGWCompiler
    compiler = findMinGWCompiler(configuration=configuration)
    createVariants(platform, hostArchitecture, compiler)
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
      createVariants(platform, architecture, compiler)
  except CompilerNotFoundError:
    pass
