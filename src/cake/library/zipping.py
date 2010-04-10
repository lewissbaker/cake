"""Zip Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.engine import Script
from cake.library import Tool, getPathAndTask
import cake.filesys
import zipfile
import os
import os.path
import time

def _extractFile(engine, zipfile, zipinfo, targetDir, onlyNewer):
  """Extract the ZipInfo object to a physical file at targetDir.
  """
  targetFile = os.path.join(targetDir, zipinfo.filename)
  
  if zipinfo.filename[-1] == '/':
    # The zip info corresponds to a directory.
    cake.filesys.makeDirs(targetFile)
  else:
    # The zip info corresponds to a file.
    year, month, day, hour, minute, second = zipinfo.date_time
    zipTime = time.mktime(time.struct_time((year, month, day, hour, minute, second, 0, 0, 0)))
    
    if onlyNewer and os.path.isfile(targetFile):
      mtime = os.stat(targetFile).st_mtime
      if zipTime == mtime:
        # Assume the zip and the extract are the same file.
        return
    
    engine.logger.outputInfo("Extracting %s\n" % targetFile)
    
    try:
      cake.filesys.makeDirs(os.path.dirname(targetFile))
      f = open(targetFile, 'wb')
      try:
        f.write(zipfile.read(zipinfo.filename))
      finally:
        f.close()
    except Exception, e:
      engine.raiseError("Failed to extract file %s: %s\n" % (zipinfo.filename, str(e)))

    # Set the file modification time to match the zip time
    os.utime(targetFile, (zipTime, zipTime))

def _writeFile(engine, file, target, sourcePath, targetPath):
  utcTime = time.gmtime(os.stat(sourcePath).st_mtime)
  targetPath = targetPath.replace("\\", "/") # Zips use forward slashes
  
  engine.logger.outputInfo("Adding %s to %s\n" % (sourcePath, target))
  
  if os.path.isdir(sourcePath):
    if not targetPath.endswith("/"):
      targetPath += "/" # Trailing slash denotes directory for some zip packages

    zi = zipfile.ZipInfo(targetPath, utcTime[0:6])
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0x00000010L # FILE_ATTRIBUTE_DIRECTORY
    file.writestr(zi, "")
  else:  
    f = open(sourcePath, "rb")
    try:
      data = f.read()
    finally:
      f.close()
    
    zi = zipfile.ZipInfo(targetPath, utcTime[0:6])
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0x00000020L # FILE_ATTRIBUTE_ARCHIVE
    file.writestr(zi, data)

def _walkTree(path):
  """Recursively walk a directory tree.
  """
  for dirPath, dirNames, fileNames in os.walk(path):
    for name in dirNames:
      yield os.path.join(dirPath, name)
      
    for name in fileNames:
      yield os.path.join(dirPath, name)

class ZipTool(Tool):
  
  def extract(
    self,
    targetDir,
    source,
    onlyNewer=True,
    removeStale=False,
    includeMatch=None,
    excludeMatch=None,
    ):
    """Extract all files in a Zip to the specified path.
  
    @param targetDir: The directory to extract files to.
    @type targetDir: string
    @param source: Path to the zip file to extract files from.
    @type source: string
    @param onlyNewer: Only extract files that are newer than those in
    the target directory.
    @type onlyNewer: bool
    @param removeStale: Remove files and directories in the target
    directory that no longer exist in the zip.
    @type removeStale: bool 
    @param includeMatch: A callable used to decide whether to include
    certain files in the extraction. This could be a python callable that
    returns True to include the file or False to exclude it, or a regular
    expression function such as re.compile().match or re.match.
    @type includeMatch: any callable 
    @param excludeMatch: A callable used to decide whether to exclude certain
    files from being extracted. This could be a python callable that
    returns True to exclude the file or False to include it, or a regular
    expression function such as re.compile().match or re.match.
    @type excludeMatch: any callable 
    
    @return: A task that will complete when the extraction has finished.
    @rtype: L{Task} 
    """
    if not isinstance(targetDir, basestring):
      raise TypeError("targetDir must be a string")

    sourcePath, sourceTask = getPathAndTask(source)

    engine = Script.getCurrent().engine
    
    def doIt():
      file = zipfile.ZipFile(sourcePath, "r")
      try:
        zipInfos = file.infolist()
        
        if includeMatch is not None:
          newZipInfos = []
          for zipInfo in zipInfos:
            if includeMatch(zipInfo.filename):
              newZipInfos.append(zipInfo)
          zipInfos = newZipInfos

        if excludeMatch is not None:
          newZipInfos = []
          for zipInfo in zipInfos:
            if not excludeMatch(zipInfo.filename):
              newZipInfos.append(zipInfo)
          zipInfos = newZipInfos
        
        if removeStale:
          zipFiles = set()
          for zipInfo in zipInfos:
            path = os.path.join(targetDir, zipInfo.filename)
            zipFiles.add(os.path.normpath(os.path.normcase(path)))
          
          for path in _walkTree(targetDir):
            if os.path.normcase(path) not in zipFiles:
              engine.logger.outputInfo("Deleting %s\n" % path)
              if os.path.isdir(path):
                cake.filesys.removeTree(path)
              else:
                cake.filesys.remove(path)
        
        for zipinfo in zipInfos:
          _extractFile(engine, file, zipinfo, targetDir, onlyNewer)   
      finally:
        file.close()

    task = engine.createTask(doIt)
    task.startAfter(sourceTask)
    return task

  def compress(
    self,
    target,
    source,
    onlyNewer=True,
    removeStale=True,
    includeMatch=None,
    excludeMatch=None,
    ):
    """Extract all files in a Zip to the specified path.
  
    @param target: Path to the zip file to add files to.
    @type target: string
    @param source: Path to the source file or directory to add.
    @type source: string
    @param onlyNewer: Only add files that are newer than those in
    the zip file. Otherwise all files are re-added every time.
    @type onlyNewer: bool
    @param removeStale: Remove files and directories in the zip
    file that no longer exist in the source directory.
    @type removeStale: bool 
    @param includeMatch: A callable used to decide whether to include
    certain files in the zip file. This could be a python callable that
    returns True to include the file or False to exclude it, or a regular
    expression function such as re.compile().match or re.match.
    @type includeMatch: any callable 
    @param excludeMatch: A callable used to decide whether to exclude certain
    files from the zip file. This could be a python callable that
    returns True to exclude the file or False to include it, or a regular
    expression function such as re.compile().match or re.match.
    @type excludeMatch: any callable 
    
    @return: A task that will complete when the compression has finished.
    @rtype: L{Task} 
    """
    if not isinstance(target, basestring):
      raise TypeError("target  must be a string")

    sourcePath, sourceTask = getPathAndTask(source)

    engine = Script.getCurrent().engine
    
    def doIt():
      toZip = {}
      if os.path.isdir(source):
        firstChar = len(source)+1
        for path in _walkTree(source):
          targetPath = path[firstChar:] # Strip the source dir name
          if includeMatch is not None and not includeMatch(targetPath):
            continue
          if excludeMatch is not None and excludeMatch(targetPath):
            continue
          toZip[os.path.normcase(targetPath)] = (path, targetPath)
      else:
        targetPath = os.path.basename(source)
        toZip[os.path.normcase(targetPath)] = (source, targetPath)
      
      if onlyNewer:
        recreate = False
      else:
        recreate = True # Always rebuild
      
      if not recreate:
        try:
          file = zipfile.ZipFile(target, "r")
          try:
            zipInfos = file.infolist()
          finally:
            file.close()
          
          fromZip = {}
          for zipInfo in zipInfos:
            path = os.path.normpath(os.path.normcase(zipInfo.filename))
            fromZip[path] = zipInfo
        except EnvironmentError:
          recreate = True # File doesn't exist or is invalid

      if not recreate and onlyNewer:
        for path, sourceTarget in toZip.iteritems():
          zipInfo = fromZip.get(path, None)
          if zipInfo is not None:
            utcTime = time.gmtime(os.stat(sourceTarget[0]).st_mtime)
            zipTime = utcTime[0:5] + (
              utcTime[5] & 0xFE, # Zip only saves 2 second resolution
              )              
            if zipTime != zipInfo.date_time:
              # We must recreate the zip to update files
              recreate = True
              break
          
        if not recreate and removeStale:
          for path in fromZip.iterkeys():
            if path not in toZip:
              # We must recreate the zip to remove files
              recreate = True
              break
      
      if recreate:
        cake.filesys.makeDirs(os.path.dirname(target))
        file = zipfile.ZipFile(target, "w")
        try:
          for sourcePath, targetPath in toZip.itervalues():
            _writeFile(engine, file, target, sourcePath, targetPath)
        finally:
          file.close()
      else:
        file = None
        try:
          for sourcePath, targetPath in toZip.itervalues():
            path = os.path.normcase(targetPath)
            if path not in fromZip:
              if file is None:
                file = zipfile.ZipFile(target, "a")
              _writeFile(engine, file, target, sourcePath, targetPath)
        finally:
          if file is not None:
            file.close()

    task = engine.createTask(doIt)
    task.startAfter(sourceTask)
    return task
    