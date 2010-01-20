from cake.builders import compiler, script, env, filesys

script.include(filesys.cwd("include.cake"))

sources = filesys.cwd([
  "main.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}"),
  sources=sources,
  )

compiler.program(
  target=env.expand("${BUILD}/test"),
  sources=objects,
  )
