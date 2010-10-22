#-------------------------------------------------------------------------------
# Configuration to build a dummy program and provide project generation.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.script import ScriptTool
from cake.library.project import ProjectTool
from cake.library.compilers.dummy import DummyCompiler

engine = Script.getCurrent().engine
configuration = Script.getCurrent().configuration

# Make sure we give the variant a name. By default this is what the project
# generator will use as the configuration name. To override this you can set
# any of the following ProjectTool variables individually:
# - projectConfigName
# - projectPlatformName
# - solutionConfigName
# - solutionPlatformName
variant = Variant(target="Release")
variant.tools["script"] = ScriptTool(configuration=configuration)

# Create the project tool, only enabled during project generation.
# Add a build success callback that will do the actual project generation.
projectTool = variant.tools["project"] = ProjectTool(configuration=configuration)
projectTool.enabled = engine.options.createProjects
engine.addBuildSuccessCallback(projectTool.build)

# Create a compiler that is disabled during project generation.
compiler = variant.tools["compiler"] = DummyCompiler(configuration=configuration)
compiler.enabled = not engine.options.createProjects

configuration.addVariant(variant)
