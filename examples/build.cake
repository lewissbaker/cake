#-------------------------------------------------------------------------------
# This script recursively builds all examples that are known to work.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler, variant

import cake.system

script.execute([
  "compileprogram/build.cake",
  "compilescriptresult/build.cake",
  "copydirectory/build.cake",
  "copyfile/build.cake",
  "createproject/build.cake",
  "env/build.cake",
  "findfiles/build.cake",
  "pythontool/build.cake",
  "queryvariant/build.cake",
  "scriptresult/build.cake",
  "unzip/build.cake",
  "uselibrary/main/build.cake",
  "usemodule/main/build.cake",
  "usepch/build.cake",
  "zip/build.cake",
  ])

# Cppdotnet example only compiles under MSVC.
if compiler.name == "msvc":
  script.execute("cppdotnet/program/build.cake")

# Shell example builds an executable that only runs on the host architecture.
if variant.architecture == cake.system.architecture().lower():
  script.execute("shell/build.cake")
