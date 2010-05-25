# Script to build printer library
from cake.tools import compiler, env, script

# Add the .h include path
compiler.addIncludePath(script.cwd("include"))

# List of includes
includes = script.cwd("include", [
  "printer.h",
  ])

# List of sources
sources = script.cwd("source", [
  "printer.cpp",
  ])

# Build objects
objects = compiler.objects(
  targetDir=env.expand("${BUILD}/uselibrary/printer/obj"),
  sources=sources,
  )

# Build library
lib = compiler.library(
  target=env.expand("${BUILD}/uselibrary/printer/lib/printer"),
  sources=objects,
  )
script.setResult(library=lib)
