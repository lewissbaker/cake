#-------------------------------------------------------------------------------
# Script that can be included to use the printer library.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Add the libraries include path.
compiler.addIncludePath(script.cwd("include"))

# Add the library. All subsequent program and module builds will link with it.
compiler.addLibrary(script.getResult(script.cwd("build.cake"), "library"))
