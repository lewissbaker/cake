from cake.tools import compiler, env, script

sources = script.cwd([
  "main.cpp",
  ])

# The PCH header exactly as it's included by source files
pchHeader = "pch.h"

pch = compiler.pch(
  target=env.expand("${BUILD}/usepch/obj/pch"),
  source=script.cwd("pch.cpp"),
  header=pchHeader,
  )

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/usepch/obj"),
  sources=sources,
  pch=pch,
  )

compiler.program(
  target=env.expand("${BUILD}/usepch/bin/main"),
  sources=objects + [pch],
  )
