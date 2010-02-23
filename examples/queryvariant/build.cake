from cake.tools import variant

if variant.platform in ["windows"]:
  print "Current platform is '%s'." % variant.platform
else:
  print "Unknown platform '%s'." % variant.platform

if variant.release in ["debug", "optimised"]:
  print "Current release is '%s'." % variant.release
else:
  print "Unknown release '%s'." % variant.release

if variant.compiler in ["gcc", "msvc"]:
  print "Current compiler is '%s'." % variant.compiler
else:
  print "Unknown compiler '%s'." % variant.compiler
