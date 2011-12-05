#-------------------------------------------------------------------------------
# Script used to build the .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

sources = [
  "point.cpp",
  ]

compiler.clrMode = 'safe' 

objects = compiler.objects(
  targetDir="../../build/$VARIANT/cppdotnet/assembly",
  sources=sources,
  language='c++/cli',
  )

module = compiler.module(
  target="../../build/$VARIANT/cppdotnet/assembly/point",
  sources=objects,
  )

script.setResult(module=module)
