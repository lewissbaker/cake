#-------------------------------------------------------------------------------
# Configuration to query the current variant.
#-------------------------------------------------------------------------------
from cake.engine import Script, Variant
from cake.library.variant import VariantTool
from cake.library.logging import LoggingTool
import cake.system

configuration = Script.getCurrent().configuration

# Get the current platform and architecture
hostPlatform = cake.system.platform().lower()
hostArchitecture = cake.system.architecture().lower()

# Create a variant using the current platform and architecture as keywords
variant = Variant(platform=hostPlatform, architecture=hostArchitecture)
variant.tools["variant"] = VariantTool(configuration=configuration)
variant.tools["logging"] = LoggingTool(configuration=configuration)
configuration.addVariant(variant)
