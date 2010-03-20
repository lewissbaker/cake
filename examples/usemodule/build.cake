from cake.tools import script

script.execute(script.cwd([
  "integer/build.cake",
  "main/build.cake",
  ]))
