from cake.tools import variant, logging

if variant.platform in ["windows"]:
  logging.outputInfo("Current platform is '%s'.\n" % variant.platform)
else:
  logging.outputWarning("Unknown platform '%s'.\n" % variant.platform)

if variant.release in ["debug", "release"]:
  logging.outputInfo("Current release is '%s'.\n" % variant.release)
else:
  logging.outputWarning("Unknown release '%s'.\n" % variant.release)

if variant.compiler in ["dummy", "msvc", "mingw", "gcc"]:
  logging.outputInfo("Current compiler is '%s'.\n" % variant.compiler)
else:
  logging.outputWarning("Unknown compiler '%s'.\n" % variant.compiler)
