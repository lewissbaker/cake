#-------------------------------------------------------------------------------
# Script used to build the .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

sources = script.cwd([
  "point.cpp",
  ])

compiler.clrMode = 'safe' 

objects = compiler.objects(
  targetDir=script.cwd("../../build/cppdotnet/assembly"),
  sources=sources,
  language='c++/cli',
  )

module = compiler.module(
  target=script.cwd("../../build/cppdotnet/assembly/point"),
  sources=objects,
  )

script.setResult(module=module)
