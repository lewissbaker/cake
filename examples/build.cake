#-------------------------------------------------------------------------------
# This script recursively builds all examples that are known to work.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

script.execute(script.cwd([
  "compileprogram/build.cake",
  "compilescriptresult/build.cake",
  "copyfile/build.cake",
  "env/build.cake",
  "pythontool/build.cake",
  "queryvariant/build.cake",
  "scriptresult/build.cake",
  "shell/build.cake",
  "unzip/build.cake",
  "uselibrary/main/build.cake",
  "usemodule/main/build.cake",
  "usepch/build.cake",
  "zip/build.cake",
  ]))

if compiler.name == "msvc":
  script.execute(script.cwd([
    "cppdotnet/program/build.cake",
    ]))
