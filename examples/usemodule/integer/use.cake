from cake.tools import compiler, env, filesys

compiler.addIncludePath(filesys.cwd("include"))
compiler.addLibraryPath(env.expand("${BUILD}/usemodule/integer/lib"))
compiler.addLibraryScript(filesys.cwd("build.cake"))
compiler.addLibrary("integer")
