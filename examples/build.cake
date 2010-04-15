from cake.tools import script, variant
import cake.system

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
  "zip/build.cake",
  ]))

hostPlatform = cake.system.platform().lower()
hostArchitecture = cake.system.architecture().lower()

if (
  variant.platform == hostPlatform and
  variant.architecture == hostArchitecture and
  variant.compiler != "dummy"
  ):
  script.execute(script.cwd([
    "shell/build.cake",
    ]))
   