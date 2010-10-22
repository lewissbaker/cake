#-------------------------------------------------------------------------------
# Configuration to build a .NET assembly and use it in a program.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.compilers.msvc import findMsvcCompiler

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["compiler"] = findMsvcCompiler(configuration=configuration)
configuration.addVariant(variant)
