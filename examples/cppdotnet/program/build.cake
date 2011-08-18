#-------------------------------------------------------------------------------
# This example demonstrates building then using a cpp .NET assembly in a
# program.
#
# Note that this example will only work on Windows with an MSVC compiler
# installed.
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
