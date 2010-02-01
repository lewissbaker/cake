from cake.builders import compiler, filesys, env

compiler.addIncludePath(filesys.cwd())
compiler.addLibrary("foo", script=filesys.cwd("foo.cake"))
compiler.addLibraryPath(env.expand("${BUILD}/simple2"))
