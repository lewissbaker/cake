#-------------------------------------------------------------------------------
# This example demonstrates building a program then executing it using the shell
# tool.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script, shell

# List of sources.
sources = script.cwd([
  "main.cpp",
  ])

# Build the objects.
objects = compiler.objects(
  targetDir=script.cwd("../build/shell/obj"),
  sources=sources,
  )

# Build the program.
program = compiler.program(
  target=script.cwd("../build/shell/bin/main"),
  sources=objects,
  )

# List of arguments to pass to the program.
args = [
  program.path,
  "42",
  ]

# Execute the program with the arguments above. Note that the program
# will not execute correctly as this example uses an empty file created
# by the dummy compiler.
shell.run(
  args=args,
  targets=[],
  sources=[program],
  )
