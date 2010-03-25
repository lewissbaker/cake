from cake.library.script import ScriptTool
from cake.library.filesys import FileSystemTool
from cake.library.variant import VariantTool
from cake.library.project import ProjectTool
from cake.library.env import Environment
from cake.library.compilers import CompilerNotFoundError
from cake.engine import Variant
import cake.system

hostPlatform = cake.system.platform().lower()
hostArchitecture = cake.system.architecture().lower()

base = Variant()
base.tools["script"] = ScriptTool()
base.tools["filesys"] = FileSystemTool()
base.tools["variant"] = VariantTool()
env = base.tools["env"] = Environment()
env["EXAMPLES"] = "."
projectTool = base.tools["project"] = ProjectTool()
projectTool.enabled = engine.createProjects
engine.addBuildSuccessCallback(lambda e=engine: projectTool.build(e))

def createVariants(parent):
  for release in ["debug", "release"]:
    variant = parent.clone(release=release)

    platform = variant.keywords["platform"]
    compiler = variant.keywords["compiler"]
    architecture = variant.keywords["architecture"]
    
    env = variant.tools["env"]
    env["BUILD"] = "build/" + "_".join([
      platform,
      compiler,
      architecture,
      release,
      ])
  
    compiler = variant.tools["compiler"]
    compiler.objectCachePath = "cache/obj"
    compiler.outputMapFile = True
    if release == "debug":
      compiler.debugSymbols = True
    elif release == "release":
      compiler.useFunctionLevelLinking = True
      compiler.optimisation = compiler.FULL_OPTIMISATION
    
    # Disable the compiler during project generation
    if engine.createProjects:
      compiler.enabled = False

    engine.addVariant(variant, default=True)

# Dummy
from cake.library.compilers.dummy import DummyCompiler
dummy = base.clone(platform=hostPlatform, compiler="dummy", architecture=hostArchitecture)
dummy.tools["compiler"] = DummyCompiler()
createVariants(dummy)

if cake.system.platform() == 'Windows':
  # MSVC
  from cake.library.compilers.msvc import findMsvcCompiler
  for a in ["x86", "x64", "ia64"]:
    try:
      msvc = base.clone(platform="windows", compiler="msvc", architecture=a)
      msvc.tools["compiler"] = findMsvcCompiler(architecture=a) 
      createVariants(msvc)
    except CompilerNotFoundError:
      pass

  try:
    # MinGW
    from cake.library.compilers.gcc import findMinGWCompiler
    mingw = base.clone(platform="windows", compiler="mingw", architecture=hostArchitecture)
    mingw.tools["compiler"] = findMinGWCompiler()
    createVariants(mingw)
  except CompilerNotFoundError:
    pass

try:
  # GCC
  from cake.library.compilers.gcc import findGccCompiler
  gcc = base.clone(platform=hostPlatform, compiler="gcc", architecture=hostArchitecture)
  compiler = gcc.tools["compiler"] = findGccCompiler()
  compiler.addLibrary("stdc++")
  createVariants(gcc)
except CompilerNotFoundError:
  pass
