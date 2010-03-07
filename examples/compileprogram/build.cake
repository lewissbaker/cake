from cake.tools import compiler, env, script

sources = script.cwd([
  "main.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/compileprogram/obj"),
  sources=sources,
  )

compiler.program(
  target=env.expand("${BUILD}/compileprogram/bin/main"),
  sources=objects,
  )
