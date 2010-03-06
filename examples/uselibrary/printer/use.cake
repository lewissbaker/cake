# Script to use printer library
from cake.tools import compiler, env, script

# Add the libraries include path, library path, library build script
# and library filename to the compiler.
compiler.addIncludePath(script.cwd("include"))
compiler.addLibraryPath(env.expand("${BUILD}/uselibrary/printer/lib"))
compiler.addLibraryScript(script.cwd("build.cake"))
compiler.addLibrary("printer")
