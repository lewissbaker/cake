from cake.tools import compiler, script, filesys, env

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

compiler.pdbFile = env.expand("${BUILD}/simple1/foo.pdb")

mainObj = compiler.object(
  target=env.expand("${BUILD}/simple1/main"),
  source=filesys.cwd("main.cpp"),
  pdbFile=env.expand("${BUILD}/simple1/main.pdb"),
  )

otherObjs = compiler.objects(
  targetDir=env.expand("${BUILD}/simple1"),
  sources=filesys.cwd(sources),
  )

lib = compiler.library(
  target=env.expand("${BUILD}/simple1/other"),
  sources=otherObjs,
  )

mainExe = compiler.program(
  target=env.expand("${BUILD}/simple1/main"),
  sources=[mainObj] + [lib],
  )

fooExe = filesys.copyFile(
  target=env.expand("${BUILD}/simple1/foo.exe"),
  source=mainExe,
  )
