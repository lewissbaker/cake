"""Utilities for creating hashes.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

try:
  import hashlib
  def sha1(*args):
    return hashlib.sha1(*args)
except ImportError:
  import sha
  def sha1(*args):
    return sha.new(*args) 
