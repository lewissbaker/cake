from cake.tools import compiler, env, script

compiler.addIncludePath(script.cwd("include"))

compiler.addLibraryScript(script.cwd("build.cake"))
compiler.addLibraryPath(env.expand("${BUILD}/usemodule/integer/lib"))
compiler.addLibrary("integer")

compiler.addModuleScript(script.cwd("build.cake"))
compiler.addModule(env.expand("${BUILD}/usemodule/integer/lib/integer"))
