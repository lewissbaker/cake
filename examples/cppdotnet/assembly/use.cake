from cake.tools import script, env, compiler

compiler.addIncludePath(script.cwd())
compiler.addForcedUsing(script.getResult(script.cwd("build.cake"), "module"))
