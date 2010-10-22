#-------------------------------------------------------------------------------
# Script used to build the main program.
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
