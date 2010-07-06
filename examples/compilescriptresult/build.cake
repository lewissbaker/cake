from cake.tools import env, script, compiler

otherSources = script.getResult(script.cwd('gensources.cake'), 'sources')
mainSource = script.getResult(script.cwd('gensources.cake'), 'main')

otherObjects = compiler.objects(
  targetDir=env.expand('${BUILD}/compilescriptresult/obj'),
  sources=otherSources,
  )

mainObjects = compiler.objects(
  targetDir=env.expand('${BUILD}/compilescriptresult/obj'),
  sources=[mainSource],
  )

program = compiler.program(
  target=env.expand('${BUILD}/compilescriptresult/test'),
  sources=[otherObjects, mainObjects],
  )
