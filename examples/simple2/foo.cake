from cake.tools import compiler, filesys, env

compiler.addIncludePath(filesys.cwd())

sources = filesys.cwd([
  "foo.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/simple2"),
  sources=sources,
  )

compiler.library(
  target=env.expand("${BUILD}/simple2/foo"),
  sources=objects
  )
