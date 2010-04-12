from cake.tools import variant, logging

if variant.platform in ["windows"]:
  logging.outputInfo("The platform is Windows.\n")
else:
  logging.outputInfo("The platform is not Windows.\n")

if variant.release in ["debug"]:
  logging.outputInfo("This is debug mode.\n")
else:
  logging.outputInfo("This is not debug mode.\n")

if variant.compiler in ["mingw", "gcc"]:
  logging.outputInfo("The compiler is a GNU C Compiler.\n")
elif variant.compiler in ["msvc"]:
  logging.outputInfo("The compiler is Microsoft Visual C.\n")
else:
  logging.outputInfo("The compiler is %s.\n" % variant.compiler.capitalize())
