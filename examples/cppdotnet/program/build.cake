#-------------------------------------------------------------------------------
# Script used to build the main program using a .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

script.include(script.cwd("../assembly/use.cake"))

sources = script.cwd([
  "main.cpp",
  ])

compiler.clrMode = 'safe'

objects = compiler.objects(
  targetDir=script.cwd("../../build/cppdotnet/program"),
  sources=sources,
  language='c++/cli',
  )

compiler.program(
  target=script.cwd("../../build/cppdotnet/program/main"),
  sources=objects,
  )

compiler.copyModulesTo(
  targetDir=script.cwd("../../build/cppdotnet/program"),
  )
