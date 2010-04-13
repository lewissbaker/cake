from cake.tools import script

script.execute(script.cwd([
  "compileprogram/build.cake",
  "copyfile/build.cake",
  "cppdotnet/build.cake",
  "createproject/build.cake",
  "pythontool/build.cake",
  "queryvariant/build.cake",
  "unzip/build.cake",
  "uselibrary/build.cake",
  "usemodule/build.cake",
  "usepch/build.cake",
  ]))
