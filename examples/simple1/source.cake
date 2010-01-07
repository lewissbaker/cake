from cake.builders import compiler, script, filesys, env

script.include(filesys.cwd("include.cake"))

compiler.debugSymbols = True
compiler.optimisation = compiler.PARTIAL_OPTIMISATION

sources = [
  "foo.cpp",
  "bar.cpp",
  ]

if env["PLATFORM"] == "windows":
  sources += [
    "math_win.cpp",
    ]
elif env["PLATFORM"] == "wii":
  sources += [
    "math_wii.cpp",
    ]

mainObj = compiler.object(
  target=env.expand("${BUILD}/main"),
  source="main.cpp",
  )

otherObjs = compiler.objects(
  target=env.expand("${BUILD}"),
  sources=filesys.cwd(sources),
  )

mainExe = compiler.executable(
  target=env.expand("${BUILD}/main"),
  sources=[mainObj] + otherObjs,
  )

fooExe = filesys.copyFile(
  target=env.expand("${BUILD}/foo.exe"),
  source=mainExe,
  )

print result
print compiler.includePaths
