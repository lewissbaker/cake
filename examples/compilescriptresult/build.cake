#-------------------------------------------------------------------------------
# This example demonstrates building a program from a source file. The sources
# file are generated using an external script.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

otherSources = script.getResult('gensources.cake', 'sources')
mainSource = script.getResult('gensources.cake', 'main')

otherObjects = compiler.objects(
  targetDir='../build/$TARGET/compilescriptresult/obj',
  sources=otherSources,
  )

mainObjects = compiler.objects(
  targetDir='../build/$TARGET/compilescriptresult/obj',
  sources=[mainSource],
  )

program = compiler.program(
  target='../build/$TARGET/compilescriptresult/test',
  sources=[otherObjects, mainObjects],
  )
