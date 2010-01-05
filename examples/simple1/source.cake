from cake.builders import compiler, script

script.include(script.cwd("include.cake"))

compiler.debugSymbols = True
compiler.optimisation = compiler.SOME_OPTIMISATION

result = compiler.object(
  target="main",
  source="main.cpp",
  )

print result
print compiler.includePaths
