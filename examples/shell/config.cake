#-------------------------------------------------------------------------------
# Configuration to build and execute a dummy program.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.compilers.dummy import DummyCompiler
from cake.library.shell import ShellTool
import os

configuration = Script.getCurrent().configuration

variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
variant.tools["compiler"] = DummyCompiler(configuration=configuration)
shell = variant.tools["shell"] = ShellTool(configuration=configuration)
shell.update(os.environ)
configuration.addVariant(variant)
