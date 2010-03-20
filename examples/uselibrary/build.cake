from cake.tools import script

script.execute(script.cwd([
  "main/build.cake",
  "printer/build.cake",
  ]))
