#-------------------------------------------------------------------------------
# Configuration to build a dummy program with a module dependency.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.compilers.dummy import DummyCompiler

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["compiler"] = DummyCompiler(configuration=configuration)
configuration.addVariant(variant)
