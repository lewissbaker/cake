"""Version number.

@var __version__: Version string for Cake. Useful for printing to screen.

@var __version_info__: Version tuple for Cake. Useful for comparing
whether one version is newer than another.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

__version_info__ = (0, 9, 7)
__version__ = '.'.join(str(v) for v in __version_info__)
