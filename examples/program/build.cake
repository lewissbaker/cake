from cake.tools import compiler, env, filesys

sources = filesys.cwd([
  "main.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/program/obj"),
  sources=sources,
  )

compiler.program(
  target=env.expand("${BUILD}/program/bin/main"),
  sources=objects,
  )
