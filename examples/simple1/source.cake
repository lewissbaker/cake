from cake.builders import compiler, script, filesys, env

script.include(filesys.cwd("include.cake"))

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

compiler.pdbFile = env.expand("${BUILD}/foo.pdb")

mainObj = compiler.object(
  target=env.expand("${BUILD}/main"),
  source=filesys.cwd("main.cpp"),
  pdbFile=env.expand("${BUILD}/main.pdb"),
  )

otherObjs = compiler.objects(
  targetDir=env.expand("${BUILD}"),
  sources=filesys.cwd(sources),
  )

mainExe = compiler.program(
  target=env.expand("${BUILD}/main"),
  sources=[mainObj] + otherObjs,
  )

fooExe = filesys.copyFile(
  target=env.expand("${BUILD}/foo.exe"),
  source=mainExe,
  )
