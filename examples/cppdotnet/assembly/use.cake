#-------------------------------------------------------------------------------
# Script that can be included to use the .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, compiler

compiler.addIncludePath(script.cwd())
module = script.getResult(script.cwd("build.cake"), "module")
compiler.addForcedUsing(module)
compiler.addModule(module)
