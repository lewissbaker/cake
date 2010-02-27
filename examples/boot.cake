from cake.library.script import ScriptTool
from cake.library.filesys import FileSystemTool
from cake.library.variant import VariantTool
from cake.library.env import Environment
from cake.engine import Variant

import platform

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
dummy = base.clone(platform="windows", compiler="dummy")
dummy.tools["compiler"] = DummyCompiler()

dummyDebug = dummy.clone(release="debug")
engine.addVariant(setupVariant(dummyDebug))

dummyRelease = dummy.clone(release="release")
engine.addVariant(setupVariant(dummyRelease))

if platform.system() == 'Windows':
  # Msvc
  from cake.library.compilers.msvc import findCompiler as findMsvcCompiler
  msvc = base.clone(platform="windows", compiler="msvc")
  msvc.tools["compiler"] = findMsvcCompiler() 
  
  msvcDebug = msvc.clone(release="debug")
  engine.addVariant(setupVariant(msvcDebug))
  
  msvcRelease = msvc.clone(release="release")
  engine.addVariant(setupVariant(msvcRelease))

try:
  # Gcc
  from cake.library.compilers.gcc import findCompiler as findGccCompiler
  gcc = base.clone(platform="windows", compiler="gcc")
  compiler = gcc.tools["compiler"] = findGccCompiler()
  
  # TODO: Should we move this to a runtimes.cake?
  compiler.addLibrary("supc++")
  
  gccDebug = gcc.clone(release="debug")
  engine.addVariant(setupVariant(gccDebug))
  
  gccRelease = gcc.clone(release="release")
  engine.addVariant(setupVariant(gccRelease), default=True)
except EnvironmentError:
  pass
