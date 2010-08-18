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

proj = project.project(
  target=env.expand("${BUILD}/createproject/project/createproject"),
  name="My Project",
  items={
    "Include" : includes,
    "Source" : sources,
    "" : extras,
    },
  output=program,
  )

project.solution(
  target=env.expand("${BUILD}/createproject/project/createproject"),
  projects=[proj],
  )
