#-------------------------------------------------------------------------------
# This example demonstrates building then using a cpp .NET assembly in a
# program.
#
# Note that this example will only work on Windows with an MSVC compiler
# installed.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

script.include("../assembly/use.cake")

sources = [
  "main.cpp",
  ]

compiler.clrMode = 'safe'

objects = compiler.objects(
  targetDir="../../build/$TARGET/cppdotnet/program",
  sources=sources,
  language='c++/cli',
  )

compiler.program(
  target="../../build/$TARGET/cppdotnet/program/main",
  sources=objects,
  )

compiler.copyModulesTo(
  targetDir="../../build/$TARGET/cppdotnet/program",
  )
