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

# TODO: Get a list of modules top copy from eg. the compiler.
#filesys.copyFile(
#  source=env.expand("${BUILD}/usemodule/integer/lib/integer.dll"),
#  target=env.expand("${BUILD}/usemodule/main/bin/integer.dll"),
#  )
