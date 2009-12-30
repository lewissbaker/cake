from cake.builders import compiler

compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION
compiler.addIncludePath("include")

result = compiler.object(
  target="main",
  source="main.cpp",
  )

print result