#-------------------------------------------------------------------------------
# This example demonstrates building then using a cpp .NET assembly in a
# program.
#
# Note that this example will only work on Windows with an MSVC compiler
# installed.
#-------------------------------------------------------------------------------
from cake.tools import script, msvc

script.include(script.cwd("../assembly/use.cake"))

sources = script.cwd([
  "main.cpp",
  ])

msvc.clrMode = 'safe'

objects = msvc.objects(
  targetDir=script.cwd("../../build/cppdotnet/program"),
  sources=sources,
  language='c++/cli',
  )

msvc.program(
  target=script.cwd("../../build/cppdotnet/program/main"),
  sources=objects,
  )

msvc.copyModulesTo(
  targetDir=script.cwd("../../build/cppdotnet/program"),
  )
