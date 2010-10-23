#-------------------------------------------------------------------------------
# This example demonstrates building a program from a source file. The sources
# file are generated using an external script.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

otherSources = script.getResult(script.cwd('gensources.cake'), 'sources')
mainSource = script.getResult(script.cwd('gensources.cake'), 'main')

otherObjects = compiler.objects(
  targetDir=script.cwd('../build/compilescriptresult/obj'),
  sources=otherSources,
  )

mainObjects = compiler.objects(
  targetDir=script.cwd('../build/compilescriptresult/obj'),
  sources=[mainSource],
  )

program = compiler.program(
  target=script.cwd('../build/compilescriptresult/test'),
  sources=[otherObjects, mainObjects],
  )
