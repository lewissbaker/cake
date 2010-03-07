# Script to build printer library
from cake.tools import compiler, env, script

# Use printer library (only for include paths)
script.include(script.cwd("use.cake"))

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
compiler.library(
  target=env.expand("${BUILD}/uselibrary/printer/lib/printer"),
  sources=objects,
  )
