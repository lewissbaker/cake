from cake.builders import compiler, script, filesys

script.include(filesys.cwd("include.cake"))

compiler.debugSymbols = True
compiler.optimisation = compiler.SOME_OPTIMISATION

compiler2 = compiler.clone()
compiler2.useDebugSymbols = False

mainObj = compiler.object(
  target="build/main",
  source="main.cpp",
  )

otherObjs = compiler.objects(
  target="build",
  sources=["foo.cpp", "bar.cpp"],
  )

mainExe = compiler.executable(
  target="build/main",
  sources=[mainObj] + otherObjs,
  )

fooExe = filesys.copyFile(
  target="build/foo.exe",
  source=mainExe,
  )

print result
print compiler.includePaths
