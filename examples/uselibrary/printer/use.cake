# Script to use printer library
from cake.tools import compiler, env, filesys

# Add the libraries include path, library path, library build script
# and library filename to the compiler.
compiler.addIncludePath(filesys.cwd("include"))
compiler.addLibraryPath(env.expand("${BUILD}/uselibrary/printer/lib"))
compiler.addLibraryScript(filesys.cwd("build.cake"))
compiler.addLibrary("printer")
