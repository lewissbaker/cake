"""Helpers for finding the default compiler on the current platform.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import cake.system
from cake.library.compilers import CompilerNotFoundError

def findDefaultCompiler(configuration):
  """Search for and return a C/C++ compiler for the current platform.

  On Windows, search for MSVC compiler, falling back to MinGW.
  If 64-bit Windows, prefer 64-bit compiler but fall back to 32-bit compiler.

  On Cygwin, search for GCC compiler.

  On Linux, search for GCC compiler.

  On Darwin (OSX), search for GCC compiler.
  """
  if cake.system.isCygwin():
    from cake.library.compilers.gcc import findGccCompiler
    return findGccCompiler(configuration)

  elif cake.system.isWindows():
    from cake.library.compilers.msvc import findMsvcCompiler
    try:
      return findMsvcCompiler(configuration)
    except CompilerNotFoundError:
      from cake.library.compilers.gcc import findMinGWCompiler
      return findMinGWCompiler(configuration)

  elif cake.system.isLinux():
    from cake.library.compilers.gcc import findGccCompiler
    return findGccCompiler(configuration)

  elif cake.system.isDarwin():
    from cake.library.compilers.gcc import findGccCompiler
    return findGccCompiler(configuration)

  else:
    raise CompilerNotFoundError(
      "No default compiler for platform '%s'" % cake.system.platform())
