from cake.tools import compiler, env, filesys, script

# Use the integer library.
script.include(env.expand("${EXAMPLES}/usemodule/integer/use.cake"))

sources = filesys.cwd([
  "main.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/usemodule/main/obj"),
  sources=sources,
  )

compiler.program(
  target=env.expand("${BUILD}/usemodule/main/bin/main"),
  sources=objects,
  )
