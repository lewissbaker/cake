from cake.tools import compiler, env, filesys, script
import cake.path

compiler.addIncludePath(filesys.cwd("include"))
compiler.addDefine("EXPORT")

includes = filesys.cwd("include", [
  "integer.h",
  ])

sources = filesys.cwd("source", [
  "integer.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/usemodule/integer/obj"),
  sources=sources,
  )

module = compiler.module(
  target=env.expand("${BUILD}/usemodule/main/bin/integer"),
  importLibrary=env.expand("${BUILD}/usemodule/integer/lib/integer"),
  sources=objects,
  )
