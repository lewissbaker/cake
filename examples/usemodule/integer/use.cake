from cake.tools import compiler, env, script

compiler.addIncludePath(script.cwd("include"))

compiler.addLibraryScript(script.cwd("build.cake"))
compiler.addLibrary(env.expand("${BUILD}/usemodule/integer/lib/integer"))

compiler.addModuleScript(script.cwd("build.cake"))
compiler.addModule(env.expand("${BUILD}/usemodule/integer/lib/integer"))
