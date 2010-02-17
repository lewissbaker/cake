from cake.tools import compiler, script, env, filesys

script.include(filesys.cwd("include.cake"))

sources = filesys.cwd([
  "main.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/simple2"),
  sources=sources,
  )

compiler.program(
  target=env.expand("${BUILD}/simple2/test"),
  sources=objects,
  )

script.execute(filesys.cwd("foo.cake"))