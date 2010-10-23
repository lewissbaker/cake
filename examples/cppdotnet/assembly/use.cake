#-------------------------------------------------------------------------------
# Script that can be included to use the .NET assembly.
#-------------------------------------------------------------------------------
from cake.tools import script, msvc

msvc.addIncludePath(script.cwd())
module = script.getResult(script.cwd("build.cake"), "module")
msvc.addForcedUsing(module)
msvc.addModule(module)
