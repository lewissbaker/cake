#-------------------------------------------------------------------------------
# Configuration to build a dummy program.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.filesys import FileSystemTool

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["filesys"] = FileSystemTool(configuration=configuration)
configuration.addVariant(variant)
