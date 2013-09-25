from cake.tools import compiler, script

sources = [
  script.cwd('foo.c'),
  ]

objects = compiler.objects(targetDir=script.cwd(), sources=sources)
library = compiler.library(target='foo', sources=objects)
