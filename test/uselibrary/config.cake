import cake.system

from cake.engine import Variant
from cake.script import Script

from cake.library.script import ScriptTool
from cake.library.compilers import CompilerNotFoundError
from cake.library.compilers.default import findDefaultCompiler

configuration = Script.getCurrent().configuration

# Setup the tools we want to use in the build.cake
variant = Variant()
variant.tools["script"] = ScriptTool(configuration=configuration)
try:
  variant.tools["compiler"] = findDefaultCompiler(configuration)
except CompilerNotFoundError, e:
  configuration.engine.raiseError(
    "Unable to find a suitable compiler for the test: %s" % str(e))

configuration.addVariant(variant)
