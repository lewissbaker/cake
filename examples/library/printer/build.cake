# Script to build printer library
from cake.tools import compiler, env, filesys, script

# Use printer library (only for include paths)
script.include(filesys.cwd("use.cake"))

# List of includes
includes = filesys.cwd("include", [
  "printer.h",
  ])

# List of sources
sources = filesys.cwd("source", [
  "printer.cpp",
  ])

# Build objects
objects = compiler.objects(
  targetDir=env.expand("${BUILD}/library/printer/objs"),
  sources=sources,
  )

# Build library
compiler.library(
  target=env.expand("${BUILD}/library/printer/lib/printer"),
  sources=objects,
  )
