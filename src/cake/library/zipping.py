"""Zip Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.library import Tool
from cake.target import getPath, getTask, getTasks, DirectoryTarget, FileTarget
from cake.engine import BuildError
from cake.script import Script
import cake.filesys
import cake.zipping
import zipfile
import os
import os.path
import calendar
import time

def _shouldExtractFile(engine, absTargetFile, zipTime, onlyNewer):
  
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

def _extractFile(configuration, zipFile, zipPath, zipInfo, targetDir, absTargetDir, onlyNewer):
  """Extract the ZipInfo object to a physical file at targetDir.
  """
  engine = configuration.engine
  targetFile = os.path.join(targetDir, zipInfo.filename)
  absTargetFile = os.path.join(absTargetDir, zipInfo.filename)
  
  if cake.zipping.isDirectoryInfo(zipInfo):
    # The zip info corresponds to a directory.
    cake.filesys.makeDirs(absTargetFile)
  else:
    # The zip info corresponds to a file.
    year, month, day, hour, minute, second = zipInfo.date_time
    zipTime = calendar.timegm((year, month, day, hour, minute, second, 0, 0, 0))
    
    buildArgs = []
    _, reasonToBuild = configuration.checkDependencyInfo(targetFile, buildArgs)

    if reasonToBuild is None:
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
        targets=[targetFile],
        )
      
    # Now that the file has been written successfully, save the new dependency file 
    newDependencyInfo = configuration.createDependencyInfo(
      targets=[targetFile],
      args=buildArgs,
      dependencies=[],
      )
    configuration.storeDependencyInfo(newDependencyInfo)

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

  # Check modification times of source files against those in the zip
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
        # We must recreate the entire zip to update files
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
    
    @return: A DirectoryTarget that will complete when the extraction has finished.
    @rtype: L{DirectoryTarget} 
    """
    if not isinstance(targetDir, basestring):
      raise TypeError("targetDir must be a string")

    engine = self.engine
    configuration = self.configuration
    basePath = configuration.basePath
    
    targetDir = basePath(targetDir)
    source = basePath(source)
        
    def _extract():
      sourcePath = getPath(source)
      absTargetDir = configuration.abspath(targetDir)
      zipFile = zipfile.ZipFile(configuration.abspath(sourcePath), "r")
      try:
        zipInfos = zipFile.infolist()
        
        if includeMatch is not None:
          zipInfos = [z for z in zipInfos if includeMatch(z.filename)]
        
        if removeStale:
          filesInZip = set()
          for zipInfo in zipInfos:
            filesInZip.add(os.path.normcase(os.path.normpath(zipInfo.filename)))
          
          searchDir = os.path.normpath(absTargetDir)
          for path in cake.filesys.walkTree(searchDir):
            normPath = os.path.normcase(path)
            # Skip files that also exist in the zip.
            if normPath in filesInZip:
              continue
            if engine.dependencyInfoPath is None:
              # Skip .dep files that match a file in the zip.
              p, e = os.path.splitext(normPath)
              if e == ".dep" and p in filesInZip:
                continue
            
            absPath = os.path.join(searchDir, path)
            engine.logger.outputInfo(
              "Deleting %s\n" % os.path.join(targetDir, path),
              )
            if os.path.isdir(absPath):
              cake.filesys.removeTree(absPath)
            else:
              cake.filesys.remove(absPath)
        
        for zipinfo in zipInfos:
          _extractFile(configuration, zipFile, sourcePath, zipinfo, targetDir, absTargetDir, onlyNewer)   
      finally:
        zipFile.close()

    def _run():
      try:
        _extract()
      except BuildError:
        raise
      except Exception, e:
        msg = "cake: Error extracting %s to %s: %s\n" % (
          getPath(source), targetDir, str(e))
        engine.raiseError(msg, targets=[targetDir])
        
    if self.enabled:
      task = engine.createTask(_run)
      task.lazyStartAfter(getTask(source))
    else:
      task = None

    directoryTarget = DirectoryTarget(path=targetDir, task=task)

    Script.getCurrent().getDefaultTarget().addTarget(directoryTarget)

    return directoryTarget

  def compress(
    self,
    target,
    source,
    onlyNewer=True,
    removeStale=True,
    includeMatch=None,
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
    
    @return: A FileTarget corresponding to the zip file that will be created.
    It's task will complete when the zip file has been built.
    @rtype: L{FileTarget}
    """
    if not isinstance(target, basestring):
      raise TypeError("target must be a string")

    engine = self.engine
    configuration = self.configuration
    basePath = configuration.basePath
    
    target = basePath(target)
    source = basePath(source)
    
    def _compress():
      sourceDir = getPath(source)
      absSourceDir = configuration.abspath(sourceDir)

      # Build a list of files/dirs to zip
      toZip = cake.zipping.findFilesToCompress(absSourceDir, includeMatch)

      # Check for an existing dependency info file
      buildArgs = []
      toAppend = None
      _, reasonToBuild = configuration.checkDependencyInfo(target, buildArgs)
      if reasonToBuild is None:
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
      if toAppend is None:
        # Recreate zip
        cake.filesys.makeDirs(os.path.dirname(absTargetPath))
        f = open(absTargetPath, "wb")
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
      else:
        # Append to existing zip
        f = open(absTargetPath, "r+b")
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

      # Now that the zip has been written successfully, save the new dependency file 
      newDependencyInfo = configuration.createDependencyInfo(
        targets=[target],
        args=buildArgs,
        dependencies=[],
        )
      configuration.storeDependencyInfo(newDependencyInfo)

    def _run():
      try:
        return _compress()
      except BuildError:
        raise
      except Exception, e:
        msg = "cake: Error creating %s: %s\n" % (target, str(e))
        engine.raiseError(msg, targets=[target])
      
    if self.enabled:
      task = engine.createTask(_run)
      task.lazyStartAfter(getTask(source))
    else:
      task = None

    fileTarget = FileTarget(path=target, task=task)

    currentScript = Script.getCurrent()
    currentScript.getDefaultTarget().addTarget(fileTarget)
    currentScript.getTarget(cake.path.baseName(target)).addTarget(fileTarget)

    return fileTarget
