from cake.tools import script, env, compiler

compiler.addIncludePath(script.cwd())
module = script.getResult(script.cwd("build.cake"), "module")
compiler.addForcedUsing(module)
compiler.addModule(module)
