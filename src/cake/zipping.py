"""File System Utilities.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import cake.filesys
import os
import os.path
import time
import zipfile
import zlib

def compressFile(source, target):
  """Compress the contents of a file and write it to another file.
  
  @param source: The path of the file to compress.
  @type source: string
  @param target: The path of the compressed file.
  @type target: string
  """
  data = cake.filesys.readFile(source)
  try:
    data = zlib.compress(data, 1)
  except zlib.error, e:
    raise EnvironmentError(str(e))
  cake.filesys.writeFile(target, data)

def decompressFile(source, target):
  """Decompress the contents of a file and write it to another file.
  
  @param source: The path of the file to decompress.
  @type source: string
  @param target: The path of the decompressed file.
  @type target: string
  """
  data = cake.filesys.readFile(source)
  try:
    data = zlib.decompress(data)
  except zlib.error, e:
    raise EnvironmentError(str(e))
  cake.filesys.writeFile(target, data)
  
def findFilesToCompress(sourcePath, includeMatch=None):
  """Return a dictionary of files in a given directory.
  
  @param sourcePath: The path to the file or directory to compress.
  @type sourcePath: string
  @param includeMatch: A function that returns True when a path should
  be included in the zip.
  @type includeMatch: any callable
  """
  toZip = {}
  if os.path.isdir(sourcePath):
    # Remove any trailing slash
    searchDir = os.path.normpath(sourcePath)
    for path in cake.filesys.walkTree(searchDir, includeMatch=includeMatch):
      toZip[os.path.normcase(path)] = path
  else:
    toZip[os.path.normcase(path)] = path
    
  return toZip

def isDirectoryInfo(zipInfo):
  """Determine whether a ZipInfo structure corresponds to a directory.
  
  @param zipInfo: ZipInfo to check.
  @type zipInfo: zipfile.ZipInfo
  
  @return: True if the zipInfo corresponds to a directory.
  @rtype: bool
  """
  return (zipInfo.external_attr & 0x00000010L) != 0L # FILE_ATTRIBUTE_DIRECTORY

def writeFileToZip(zipFile, sourcePath, targetPath):
  """Write a source file or directory to a zip.
  
  @param zipFile: The zip file object to write to.
  @type zipFile: zipfile.ZipFile
  @param sourcePath: The path to the source file or directory.
  @type sourcePath: string
  @param targetPath: The target path within the zip.
  @param targetPath: string 
  """
  targetPath = targetPath.replace("\\", "/") # Zips use forward slashes
  utcTime = time.gmtime(os.stat(sourcePath).st_mtime)
  
  if os.path.isdir(sourcePath):
    if not targetPath.endswith("/"):
      targetPath += "/" # Trailing slash denotes directory for some zip packages

    zi = zipfile.ZipInfo(targetPath, utcTime[0:6])
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0x00000010L # FILE_ATTRIBUTE_DIRECTORY
    zipFile.writestr(zi, "")
  else:  
    f = open(sourcePath, "rb")
    try:
      data = f.read()
    finally:
      f.close()
    
    zi = zipfile.ZipInfo(targetPath, utcTime[0:6])
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0x00000020L # FILE_ATTRIBUTE_ARCHIVE
    zipFile.writestr(zi, data)
    
def zipFiles(sourcePath, targetZip):
  """Zip a file or the contents of a directory.
  
  @param sourcePath: The source file or directory to zip.
  @type sourcePath: string
  @param targetZip: The path of the target zip.
  @type targetZip: string
  
  @return: A list of paths to the files and directories
  compressed.
  @rtype: list of string
  """
  toZip = findFilesToCompress(sourcePath)
  cake.filesys.makeDirs(os.path.dirname(targetZip))
  f = open(targetZip, "wb")
  try:
    zipFile = zipfile.ZipFile(f, "w")
    for originalPath in toZip.itervalues():
      sourceFilePath = os.path.join(sourcePath, originalPath)
      writeFileToZip(zipFile, sourceFilePath, originalPath)
    zipFile.close()
  finally:
    f.close()
  return toZip.values()
