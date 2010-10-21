#-------------------------------------------------------------------------------
# Script used to build the integer module.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Add the .h include path.
compiler.addIncludePath(script.cwd("include"))

# Set a define to say we are building the module (read in 'include/module.h')
compiler.addDefine("EXPORT_MODULE", "1")

# List of includes.
includes = script.cwd("include", [
  "integer.h",
  ])

# List of sources.
sources = script.cwd("source", [
  "integer.cpp",
  ])

# Build the objects.
objects = compiler.sharedObjects(
  targetDir=script.cwd("../../build/usemodule/integer/obj"),
  sources=sources,
  )

# Build the module. Also build a matching import library. And set the install
# name for Macintosh builds.
module = compiler.module(
  target=script.cwd("../../build/usemodule/integer/lib/integer"),
  importLibrary=script.cwd("../../build/usemodule/integer/lib/integer"),
  installName="@rpath/integer",
  sources=objects,
  )

# Set the 'module' result of this script to the module we built above, and the
# 'library' result to the matching import library.
script.setResult(
  module=module,
  library=module.library,
  )
