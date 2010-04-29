from cake.tools import compiler, env, script

compiler.addIncludePath(script.cwd("include"))
compiler.addDefine("EXPORT")

includes = script.cwd("include", [
  "integer.h",
  ])

sources = script.cwd("source", [
  "integer.cpp",
  ])

objects = compiler.sharedObjects(
  targetDir=env.expand("${BUILD}/usemodule/integer/obj"),
  sources=sources,
  )

module = compiler.module(
  target=env.expand("${BUILD}/usemodule/integer/lib/integer"),
  importLibrary=env.expand("${BUILD}/usemodule/integer/lib/integer"),
  installName=env.expand("@rpath/integer"),
  sources=objects,
  )
