from cake.tools import variant

import sys

if variant.platform in ["windows"]:
  sys.stdout.write("Current platform is '%s'.\n" % variant.platform)
else:
  sys.stderr.write("Unknown platform '%s'.\n" % variant.platform)

if variant.release in ["debug", "release"]:
  sys.stdout.write("Current release is '%s'.\n" % variant.release)
else:
  sys.stderr.write("Unknown release '%s'.\n" % variant.release)

if variant.compiler in ["dummy", "msvc", "mingw", "gcc"]:
  sys.stdout.write("Current compiler is '%s'.\n" % variant.compiler)
else:
  sys.stderr.write("Unknown compiler '%s'.\n" % variant.compiler)
