from cake.tools import script, variant

if variant.compiler == "msvc":
  script.execute(script.cwd([
    "assembly/build.cake",
    "program/build.cake",
    ]))
