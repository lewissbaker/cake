from cake.tools import script, env, compiler, filesys

script.include(script.cwd("../assembly/use.cake"))

sources = script.cwd([
  "main.cpp",
  ])

compiler.clrMode = 'safe'

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/cppdotnet/program"),
  sources=sources,
  language='c++/cli',
  )

compiler.program(
  target=env.expand("${BUILD}/cppdotnet/program/main"),
  sources=objects,
  )

compiler.copyModulesTo(
  targetDir=env.expand("${BUILD}/cppdotnet/program"),
  )
