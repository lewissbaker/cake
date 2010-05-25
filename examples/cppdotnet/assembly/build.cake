from cake.tools import script, env, compiler

sources = script.cwd([
  "point.cpp",
  ])

compiler.clrMode = 'safe' 

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/cppdotnet/assembly"),
  sources=sources,
  language='c++/cli',
  )

module = compiler.module(
  target=env.expand("${BUILD}/cppdotnet/assembly/point"),
  sources=objects,
  )

script.setResult(module=module)
