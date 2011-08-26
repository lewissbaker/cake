#-------------------------------------------------------------------------------
# Script that can be included to use the integer module.
#-------------------------------------------------------------------------------
from cake.tools import compiler, script

# Save a reference to the build script since we use it twice.
buildScript = script.get("build.cake")

# Add the modules include path.
compiler.addIncludePath("include")

# Add the library. All subsequent program and module builds will link with it.
compiler.addLibrary(buildScript.getResult("library"))

# Add the module. Subsequent calls to compiler.copyModulesTo() will now also
# copy this module.
compiler.addModule(buildScript.getResult("module"))
