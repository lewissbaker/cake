#-------------------------------------------------------------------------------
# This example demonstrates using the EnvTool to set and retrieve values
#-------------------------------------------------------------------------------
from cake.tools import env, logging

# Set a value.
env["Version"] = "1.2.3"
env["OutputDir"] = "path/to"

# Retrieve a value.
version = env["Version"]
outputDir = env["OutputDir"]
logging.outputInfo("Version is %s.\n" % version)
logging.outputInfo("OutputDir is %s.\n" % outputDir)

# Expand values.
buildVersion = env.expand("build_${Version}")
buildDir = env.expand("$OutputDir/build")
logging.outputInfo("buildVersion is %s.\n" % buildVersion)
logging.outputInfo("buildDir is %s.\n" % buildDir)

# Delete a value given its key.
del env["Version"]

# Test for existence of a value.
if "Version" in env:
  logging.outputInfo("Version is still in env.\n")
else:
  logging.outputInfo("Version is no longer in env.\n")

# Get a value or return a default value if not found.
version = env.get("Version", None)
if version is None:
  logging.outputInfo("The result is None.\n")
else:
  logging.outputInfo("The result is not None.\n")

# Set a value only if it doesn't exist.
version = env.setDefault("Version", "2.3.4")
logging.outputInfo("Version after setDefault is %s.\n" % version)

# Update key/values with those passed in.
env.update({
  "Version":"3.4.5",
  "OutputDir":outputDir,
  })
logging.outputInfo("Version after dict update is %s.\n" % env["Version"])

env.update(
  Version="4.5.6",
  OutputDir=outputDir,
  )
logging.outputInfo("Version after keyword update is %s.\n" % env["Version"])

# Append keyword arguments to the environment.
env.append(Version=".7.8.9",NewKey="SomeSecondValue")
logging.outputInfo("Version after append is %s.\n" % env["Version"])
logging.outputInfo("NewKey after append is %s.\n" % env["NewKey"])

# Prepend keyword arguments to the environment.
env.prepend(Version="1.2.3.",NewKey=["SomeFirstValue"])
logging.outputInfo("Version after prepend is %s.\n" % env["Version"])
logging.outputInfo("NewKey after prepend is %s.\n" % env["NewKey"])

# Replace keyword arguments in the environment.
env.replace(Version="7.8.9",NewKey="SomeNewValue")
logging.outputInfo("Version after replace is %s.\n" % env["Version"])
logging.outputInfo("NewKey after replace is %s.\n" % env["NewKey"])

# Choose a value depending on the key passed in.
env["platform"] = "windows"
sourceFile = {
  "windows":"Win32.cpp",
  "darwin":"Darwin.cpp",
  }.get(env["platform"], "OtherPlatforms.cpp")
logging.outputInfo("sourceFile is %s.\n" % sourceFile)
