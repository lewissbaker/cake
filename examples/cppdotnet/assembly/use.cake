#-------------------------------------------------------------------------------
# Script that can be included to use the .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

compiler.addIncludePath(".")
module = script.getResult("build.cake", "module")
compiler.addForcedUsing(module)
compiler.addModule(module)
