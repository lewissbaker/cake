from cake.library.script import ScriptTool
from cake.library.filesys import FileSystemTool
from cake.library.variant import VariantTool
from cake.library.env import Environment
from cake.library.compilers import CompilerNotFoundError
from cake.engine import Variant

import platform

currentPlatform = platform.system().lower()

def setupVariant(variant):
  platform = variant.keywords["platform"]
  compilerName = variant.keywords["compiler"]
  release = variant.keywords["release"]
  compiler = variant.tools["compiler"]
  
  env = variant.tools["env"]
  env["BUILD"] = "build/" + "_".join([
    platform,
    compilerName,
    compiler.architecture,
    release,
    ])

  if release == "debug":
    compiler.debugSymbols = True
  elif release == "release":
    compiler.optimisation = compiler.FULL_OPTIMISATION

  return variant
  
base = Variant()
base.tools["script"] = ScriptTool()
base.tools["filesys"] = FileSystemTool()
base.tools["variant"] = VariantTool()
env = base.tools["env"] = Environment()
env["EXAMPLES"] = "."

# Dummy
from cake.library.compilers.dummy import DummyCompiler
dummy = base.clone(platform=currentPlatform, compiler="dummy")
dummy.tools["compiler"] = DummyCompiler()

dummyDebug = dummy.clone(release="debug")
engine.addVariant(setupVariant(dummyDebug), default=True)

dummyRelease = dummy.clone(release="release")
engine.addVariant(setupVariant(dummyRelease))

if platform.system() == 'Windows':
  try:
    # Msvc
    from cake.library.compilers.msvc import findMsvcCompiler
    msvc = base.clone(platform="windows", compiler="msvc")
    msvc.tools["compiler"] = findMsvcCompiler() 
    
    msvcDebug = msvc.clone(release="debug")
    engine.addVariant(setupVariant(msvcDebug), default=True)
    
    msvcRelease = msvc.clone(release="release")
    engine.addVariant(setupVariant(msvcRelease))
  except CompilerNotFoundError:
    pass

  try:
    # MinGW
    from cake.library.compilers.gcc import findMinGWCompiler
    mingw = base.clone(platform="windows", compiler="mingw")
    compiler = mingw.tools["compiler"] = findMinGWCompiler()
    
    mingwDebug = mingw.clone(release="debug")
    engine.addVariant(setupVariant(mingwDebug), default=True)
    
    mingwRelease = mingw.clone(release="release")
    engine.addVariant(setupVariant(mingwRelease))
  except CompilerNotFoundError:
    pass

try:
  # Gcc
  from cake.library.compilers.gcc import findGccCompiler
  gcc = base.clone(platform=currentPlatform, compiler="gcc")
  compiler = gcc.tools["compiler"] = findGccCompiler()
  
  # TODO: Should we move this to a runtimes.cake?
  compiler.addLibrary("supc++")
  
  gccDebug = gcc.clone(release="debug")
  engine.addVariant(setupVariant(gccDebug), default=True)
  
  gccRelease = gcc.clone(release="release")
  engine.addVariant(setupVariant(gccRelease))
except CompilerNotFoundError:
  pass
