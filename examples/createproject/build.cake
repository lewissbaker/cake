from cake.tools import compiler, env, script, project

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
  targetDir=env.expand("${BUILD}/createproject/obj"),
  sources=sources,
  )

program = compiler.program(
  target=env.expand("${BUILD}/createproject/bin/main"),
  sources=objects,
  )

project.project(
  target=script.cwd("createproject"),
  name="My Project",
  items={
    "Include" : includes,
    "Source" : sources,
    "" : extras,
    },
  output=program,
  version=project.VS2008,
  )

project.solution(
  target=script.cwd("createproject"),
  projects=[script.cwd("createproject")],
  version=project.VS2008,
  )
