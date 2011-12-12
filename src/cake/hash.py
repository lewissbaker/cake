"""Utilities for creating hashes.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import binascii

try:
  import hashlib
  def sha1(*args, **kwargs):
    return hashlib.sha1(*args, **kwargs)
  def md5(*args, **kwargs):
    return hashlib.md5(*args, **kwargs)
except ImportError:
  import sha
  def sha1(*args, **kwargs):
    return sha.new(*args, **kwargs) 
  import md5 as md5lib
  def md5(*args, **kwargs):
    return md5lib.new(*args, **kwargs) 

def hexlify(digest):
  """Get the hex-string representation of a digest.

  @param digest: A series of bytes comprising the digest.
  eg. A SHA-1 digest will be 20 bytes.
  @type digest: str/bytes

  @return: A string containing the hexadecimal string representation of the
  digest.
  @rtype: unicode
  """
  return binascii.hexlify(digest).decode("utf8")
