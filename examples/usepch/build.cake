#-------------------------------------------------------------------------------
# Script used to build the main program.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# List of sources.
sources = script.cwd([
  "main.cpp",
  ])

# The precompiled header exactly as it's included by source files.
pchHeader = "pch.h"

# Build the precompiled header.
pch = compiler.pch(
  target=script.cwd("../build/usepch/obj/pch"),
  source=script.cwd("pch.cpp"),
  header=pchHeader,
  )

# Build the objects. Use the precompiled header built above.
objects = compiler.objects(
  targetDir=script.cwd("../build/usepch/obj"),
  sources=sources,
  pch=pch,
  )

# Build the program. The precompiled header must be added to the list of sources
# for compilers such as MSVC.
compiler.program(
  target=script.cwd("../build/usepch/bin/main"),
  sources=objects + [pch],
  )
