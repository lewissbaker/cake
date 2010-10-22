#-------------------------------------------------------------------------------
# Configuration to run a python function.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.logging import LoggingTool

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["logging"] = LoggingTool(configuration=configuration)
configuration.addVariant(variant)
