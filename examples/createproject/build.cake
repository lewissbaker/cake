#-------------------------------------------------------------------------------
# Script used to build the main program and generate projects.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script, project

includes = script.cwd([
  "main.h",
  ])

sources = script.cwd([
  "main.cpp",
  ])

extras = script.cwd([
  "build.cake",
  "readme.txt",
  ])

objects = compiler.objects(
  targetDir=script.cwd("../build/createproject/obj"),
  sources=sources,
  )

program = compiler.program(
  target=script.cwd("../build/createproject/bin/main"),
  sources=objects,
  )

proj = project.project(
  target=script.cwd("../build/createproject/project/createproject"),
  name="My Project",
  items={
    "Include" : includes,
    "Source" : sources,
    "" : extras,
    },
  output=program,
  )

project.solution(
  target=script.cwd("../build/createproject/project/createproject"),
  projects=[proj],
  )
