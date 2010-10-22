#-------------------------------------------------------------------------------
# Configuration to get the result of a script.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
configuration.addVariant(variant)
