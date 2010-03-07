from cake.tools import compiler, env, script

compiler.addIncludePath(script.cwd("include"))
compiler.addLibraryPath(env.expand("${BUILD}/usemodule/integer/lib"))
compiler.addLibraryScript(script.cwd("build.cake"))
compiler.addLibrary("integer")
