#-------------------------------------------------------------------------------
# Script used to query the current variant.
#-------------------------------------------------------------------------------
from cake.tools import variant, logging

if variant.platform in ["windows"]:
  logging.outputInfo("The platform is Windows.\n")
else:
  logging.outputInfo("The platform is not Windows.\n")

if variant.architecture in ["x86"]:
  logging.outputInfo("The architecture is Intel based x86.\n")
else:
  logging.outputInfo("This architecture is %s.\n" % variant.architecture)
