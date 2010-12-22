#-------------------------------------------------------------------------------
# Script used to build the main program and it's associated project.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script, project

# List of includes.
includes = script.cwd([
  "main.h",
  ])

# List of sources.
sources = script.cwd([
  "main.cpp",
  ])

# List of extra files.
extras = script.cwd([
  "build.cake",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir=script.cwd("../../build/createproject/obj"),
  sources=sources,
  )

# Build the program.
program = compiler.program(
  target=script.cwd("../../build/createproject/bin/main"),
  sources=objects,
  )

# Build the project file.
proj = project.project(
  target=script.cwd("../../build/createproject/project/createproject"),
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
