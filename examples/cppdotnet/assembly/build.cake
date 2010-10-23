#-------------------------------------------------------------------------------
# Script used to build the .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, msvc

sources = script.cwd([
  "point.cpp",
  ])

msvc.clrMode = 'safe' 

objects = msvc.objects(
  targetDir=script.cwd("../../build/cppdotnet/assembly"),
  sources=sources,
  language='c++/cli',
  )

module = msvc.module(
  target=script.cwd("../../build/cppdotnet/assembly/point"),
  sources=objects,
  )

script.setResult(module=module)
