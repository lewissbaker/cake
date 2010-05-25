from cake.tools import compiler, env, script

buildScript = script.get(script.cwd("build.cake"))

compiler.addIncludePath(script.cwd("include"))
compiler.addLibrary(buildScript.getResult("library"))
compiler.addModule(buildScript.getResult("module"))
