#-------------------------------------------------------------------------------
# Script used to build the main program and it's associated project.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script, project

# List of includes.
includes = [
  "main.h",
  ]

# List of sources.
sources = [
  "main.cpp",
  ]

# List of extra files.
extras = [
  "build.cake",
  ]

# Build the objects.
objects = compiler.objects(
  targetDir="../../build/$VARIANT/createproject/obj",
  sources=sources,
  )

# Build the program.
program = compiler.program(
  target="../../build/$VARIANT/createproject/bin/main",
  sources=objects,
  )

# Build the project file.
proj = project.project(
  target="../../build/project/createproject/createproject",
  name="My Project",
  items={
    "Include" : includes,
    "Source" : sources,
    "" : extras,
    },
  output=program,
  )

# Set the 'project' result of this script to the project we built above.
script.setResult(project=proj)
