"""Zip Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.library import Tool, getPath, getTask
import cake.filesys
import cake.zipping
import zipfile
import os
import os.path
import calendar
import time

def _shouldExtractFile(engine, absTargetFile, zipTime, onlyNewer):
  
  if engine.forceBuild:
    return "rebuild has been forced"
  
  if not onlyNewer:
    return "onlyNewer is False" # Always rebuild

  try:
    mtime = os.stat(absTargetFile).st_mtime
  except EnvironmentError:
    return "it doesn't exist" 

  if zipTime != mtime:
    # Assume the zip and the extract are the same file.
    return "it has been changed"
    
  return None

def _extractFile(engine, zipFile, zipPath, zipInfo, targetDir, absTargetDir, onlyNewer):
  """Extract the ZipInfo object to a physical file at targetDir.
  """
  targetFile = os.path.join(targetDir, zipInfo.filename)
  absTargetFile = os.path.join(absTargetDir, zipInfo.filename)
  
  if cake.zipping.isDirectoryInfo(zipInfo):
    # The zip info corresponds to a directory.
    cake.filesys.makeDirs(absTargetFile)
  else:
    # The zip info corresponds to a file.
    year, month, day, hour, minute, second = zipInfo.date_time
    zipTime = calendar.timegm((year, month, day, hour, minute, second, 0, 0, 0))
    
    reasonToBuild = _shouldExtractFile(engine, absTargetFile, zipTime, onlyNewer)
    if reasonToBuild is None:
      return # Target is up to date

    engine.logger.outputDebug(
      "reason",
      "Extracting '" + targetFile + "' because " + reasonToBuild + ".\n",
      )
    
    engine.logger.outputInfo("Extracting %s\n" % targetFile)
    
    try:
      cake.filesys.writeFile(absTargetFile, zipFile.read(zipInfo.filename))
    except Exception, e:
      engine.raiseError(
        "Failed to extract file %s from zip %s: %s\n" % (
          zipInfo.filename,
          zipPath,
          str(e),
          ),
        )

    # Set the file modification time to match the zip time
    os.utime(absTargetFile, (zipTime, zipTime))

def _shouldCompress(
  configuration,
  sourcePath,
  targetPath,
  toZip,
  onlyNewer,
  removeStale,
  ):
  
  if configuration.engine.forceBuild:
    return None, "rebuild has been forced"
  
  if not onlyNewer:
    return None, "onlyNewer is False" # Always rebuild
  
  absSourcePath = configuration.abspath(sourcePath)
  absTargetPath = configuration.abspath(targetPath)

  # Try to open an existing zip file
  try:
    file = zipfile.ZipFile(absTargetPath, "r")
    try:
      zipInfos = file.infolist()
    finally:
      file.close()
    
    # Build a list of files/dirs in the current zip
    fromZip = {}
    for zipInfo in zipInfos:
      path = os.path.normpath(os.path.normcase(zipInfo.filename))
      fromZip[path] = zipInfo
  except EnvironmentError:
    # File doesn't exist or is invalid
    return None, "'" + targetPath + "' doesn't exist" 

  if onlyNewer:
    for casedPath, originalPath in toZip.iteritems():
      zipInfo = fromZip.get(casedPath, None)

      # Not interested in modified directories
      if zipInfo is not None and not cake.zipping.isDirectoryInfo(zipInfo):
        absSourceFilePath = os.path.join(absSourcePath, originalPath)
        utcTime = time.gmtime(os.stat(absSourceFilePath).st_mtime)
        zipTime = utcTime[0:5] + (
          utcTime[5] & 0xFE, # Zip only saves 2 second resolution
          )              
        if zipTime != zipInfo.date_time:
          sourceFilePath = os.path.join(sourcePath, originalPath)
          # We must recreate the zip to update files
          return None, "'" + sourceFilePath + "' has been changed"
      
  if removeStale:
    for path, zipInfo in fromZip.iteritems():
      if path not in toZip:
        # We must recreate the zip to remove files
        sourceFilePath = os.path.join(sourcePath, zipInfo.filename)
        return None, "'" + sourceFilePath + "' has been removed"
  
  toAppend = []
  reasonToBuild = None
  for casedPath, originalPath in toZip.iteritems():
    if casedPath not in fromZip:
      toAppend.append(originalPath)
      if reasonToBuild is None:
        sourceFilePath = os.path.join(sourcePath, originalPath)
        reasonToBuild = "'" + sourceFilePath + "' is not in zip"
      
  return toAppend, reasonToBuild

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

    engine = self.engine
    configuration = self.configuration
    basePath = configuration.basePath
    
    targetDir = basePath(targetDir)
    source = basePath(source)
        
    def doIt():
      sourcePath = getPath(source)
      absTargetDir = configuration.abspath(targetDir)
      file = zipfile.ZipFile(configuration.abspath(sourcePath), "r")
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
            zipFiles.add(os.path.normcase(os.path.normpath(zipInfo.filename)))
          
          searchDir = os.path.normpath(absTargetDir)
          firstChar = len(searchDir) + 1
          for absPath in cake.filesys.walkTree(searchDir):
            path = absPath[firstChar:] # Strip the search dir name
            if os.path.normcase(path) not in zipFiles:
              engine.logger.outputInfo(
                "Deleting %s\n" % os.path.join(targetDir, path),
                )
              if os.path.isdir(absPath):
                cake.filesys.removeTree(absPath)
              else:
                cake.filesys.remove(absPath)
        
        for zipinfo in zipInfos:
          _extractFile(engine, file, sourcePath, zipinfo, targetDir, absTargetDir, onlyNewer)   
      finally:
        file.close()

    if self.enabled:
      sourceTask = getTask(source)

      task = engine.createTask(doIt)
      task.startAfter(sourceTask)
    else:
      task = None

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
    """Compress a source file/directory to the specified zip target path.
  
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
      raise TypeError("target must be a string")

    engine = self.engine
    configuration = self.configuration
    basePath = configuration.basePath
    
    target = basePath(target)
    source = basePath(source)
    
    def doIt():
      sourceDir = getPath(source)
      absSourceDir = configuration.abspath(sourceDir)

      # Build a list of files/dirs to zip
      toZip = cake.zipping.findFilesToCompress(absSourceDir, includeMatch, excludeMatch)

      # Figure out if we need to rebuild/append 
      toAppend, reasonToBuild = _shouldCompress(
        configuration,
        sourceDir,
        target,
        toZip,
        onlyNewer,
        removeStale,
        )
      if reasonToBuild is None:
        return # Target is up to date

      engine.logger.outputDebug(
        "reason",
        "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
        )
      
      absTargetPath = configuration.abspath(target)
      absTargetTmpPath = absTargetPath + ".tmp"
      if toAppend is None:
        # Recreate zip
        cake.filesys.makeDirs(os.path.dirname(absTargetTmpPath))
        f = open(absTargetTmpPath, "wb")
        try:
          zipFile = zipfile.ZipFile(f, "w")
          for originalPath in toZip.itervalues():
            sourcePath = os.path.join(sourceDir, originalPath)
            absSourcePath = configuration.abspath(sourcePath)
            configuration.engine.logger.outputInfo("Adding %s to %s\n" % (sourcePath, target))
            cake.zipping.writeFileToZip(zipFile, absSourcePath, originalPath)
          zipFile.close()
        finally:
          f.close()
        cake.filesys.renameFile(absTargetTmpPath, absTargetPath)
      else:
        # Append to existing zip
        cake.filesys.renameFile(absTargetPath, absTargetTmpPath)
        f = open(absTargetTmpPath, "r+b")
        try:
          zipFile = zipfile.ZipFile(f, "a")
          for originalPath in toAppend:
            sourcePath = os.path.join(sourceDir, originalPath)
            absSourcePath = configuration.abspath(sourcePath)
            configuration.engine.logger.outputInfo("Adding %s to %s\n" % (sourcePath, target))
            cake.zipping.writeFileToZip(zipFile, absSourcePath, originalPath)
          zipFile.close()
        finally:
          f.close()
        cake.filesys.renameFile(absTargetTmpPath, absTargetPath)

    if self.enabled:
      sourceTask = getTask(source)

      task = engine.createTask(doIt)
      task.startAfter(sourceTask)
    else:
      task = None
    
    return task
    