#-------------------------------------------------------------------------------
# This example demonstrates building a program then executing it using the shell
# tool.
#-------------------------------------------------------------------------------
from cake.tools import compiler, shell

# List of sources.
sources = [
  "main.cpp",
  ]

# Build the objects.
objects = compiler.objects(
  targetDir="../build/$TARGET/shell/obj",
  sources=sources,
  )

# Build the program.
program = compiler.program(
  target="../build/$TARGET/shell/bin/main",
  sources=objects,
  )

# List of arguments to pass to the program.
args = [
  program.path,
  "42",
  ]

# Execute the program with the arguments above.
shell.run(
  args=args,
  targets=[],
  sources=[program],
  )
