from cake.tools import compiler, filesys, env

compiler.addIncludePath(filesys.cwd())
compiler.addLibrary("foo")
compiler.addLibraryScript(filesys.cwd("foo.cake"))
compiler.addLibraryPath(env.expand("${BUILD}/simple2"))
