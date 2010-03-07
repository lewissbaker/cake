from cake.library.script import ScriptTool
from cake.library.filesys import FileSystemTool
from cake.library.variant import VariantTool
from cake.library.env import Environment
from cake.library.compilers import CompilerNotFoundError
from cake.engine import Variant

import platform

hostPlatform = platform.system().lower()

base = Variant()
base.tools["script"] = ScriptTool()
base.tools["filesys"] = FileSystemTool()
base.tools["variant"] = VariantTool()
env = base.tools["env"] = Environment()
env["EXAMPLES"] = "."

def createVariants(parent):
  for release in ["debug", "release"]:
    variant = parent.clone(release=release)
  
    platformName = variant.keywords["platform"]
    compilerName = variant.keywords["compiler"]
    compiler = variant.tools["compiler"]
    
    env = variant.tools["env"]
    env["BUILD"] = "build/" + "_".join([
      platformName,
      compilerName,
      compiler.architecture,
      release,
      ])
  
    if release == "debug":
      compiler.debugSymbols = True
    elif release == "release":
      compiler.optimisation = compiler.FULL_OPTIMISATION

    engine.addVariant(variant, default=True)

# Dummy
from cake.library.compilers.dummy import DummyCompiler
dummy = base.clone(platform=hostPlatform, compiler="dummy")
dummy.tools["compiler"] = DummyCompiler()
createVariants(dummy)

if platform.system() == 'Windows':
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
    mingw = base.clone(platform="windows", compiler="mingw")
    compiler = mingw.tools["compiler"] = findMinGWCompiler()
    createVariants(mingw)
  except CompilerNotFoundError:
    pass

try:
  # GCC
  from cake.library.compilers.gcc import findGccCompiler
  gcc = base.clone(platform=hostPlatform, compiler="gcc")
  compiler = gcc.tools["compiler"] = findGccCompiler()
  compiler.addLibrary("stdc++")
  createVariants(gcc)
except CompilerNotFoundError:
  pass
