#-------------------------------------------------------------------------------
# Configuration to build a zip.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.zipping import ZipTool

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["zipping"] = ZipTool(configuration=configuration)
configuration.addVariant(variant)
