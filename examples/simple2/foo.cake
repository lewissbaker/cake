from cake.builders import compiler, filesys, env

compiler.addIncludePath(filesys.cwd())

sources = filesys.cwd([
  "foo.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}"),
  sources=sources,
  )

compiler.library(
  target=env.expand("${BUILD}/foo"),
  sources=objects
  )
