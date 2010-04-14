from cake.tools import compiler, env, script, shell

sources = script.cwd([
  "main.cpp",
  ])

objects = compiler.objects(
  targetDir=env.expand("${BUILD}/shell/obj"),
  sources=sources,
  )

program = compiler.program(
  target=env.expand("${BUILD}/shell/bin/main"),
  sources=objects,
  )

args = [
  program.path,
  "42",
  ]

shell.run(
  args=args,
  targets=[],
  sources=[program],
  )
