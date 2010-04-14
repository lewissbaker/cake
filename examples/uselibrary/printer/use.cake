# Script to use printer library
from cake.tools import compiler, env, script

# Add the libraries include path, library build script and library
# filename to the compiler.
compiler.addIncludePath(script.cwd("include"))
compiler.addLibraryScript(script.cwd("build.cake"))
compiler.addLibraryPath(env.expand("${BUILD}/uselibrary/printer/lib"))
compiler.addLibrary("printer")
