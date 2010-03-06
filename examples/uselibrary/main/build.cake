# Script to build main program
from cake.tools import compiler, env, script

# Use the printer library. The libraries include path, library path
# and library filename will be added to the compilers command line
# during our object file and program builds.
script.include(env.expand("${EXAMPLES}/uselibrary/printer/use.cake"))

# List of sources
sources = script.cwd([
  "main.cpp",
  ])

# Build objects
objects = compiler.objects(
  targetDir=env.expand("${BUILD}/uselibrary/main/obj"),
  sources=sources,
  )

# Build program
compiler.program(
  target=env.expand("${BUILD}/uselibrary/main/bin/main"),
  sources=objects,
  )
