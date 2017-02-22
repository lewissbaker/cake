"""File System Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import glob
import cake.path
import cake.filesys

from cake.async import flatten, waitForAsyncResult
from cake.target import DirectoryTarget, FileTarget, getPath, getTask
from cake.library import Tool
from cake.script import Script

class FileSystemTool(Tool):
  """Tool that provides file system related utilities. 
  """

  def findFiles(self, path, recursive=True, includeMatch=None):
    """Find files and directories given a directory path.
    
    @param path: The path of the directory to search under.
    @type path: string
    
    @param recursive: Whether or not to search recursively.
    @type recursive: bool

    @param includeMatch: A callable used to decide whether to include
    certain files in the result. This could be a python callable that
    returns True to include the file or False to exclude it, or a regular
    expression function such as re.compile().match or re.match.
    @type includeMatch: any callable 
    
    @return: A sequence of paths of files and directories. The paths returned
    are relative to the 'path' argument (they are not prefixed with 'path').
    """
    configuration = self.configuration
    basePath = configuration.basePath(path)
    absPath = configuration.abspath(basePath)
    
    return cake.filesys.walkTree(
      path=absPath,
      recursive=recursive,
      includeMatch=includeMatch,
      )

  def glob(self, pathname):
    """Find files matching a particular pattern.
    
    @param pathname: A glob-style file-name pattern. eg. '*.txt'
    
    @return: A list of paths to files that match the pattern.
    """
    configuration = self.configuration
    basePath = configuration.basePath(pathname)
    absPath = configuration.abspath(basePath)
    offset = len(absPath) - len(pathname)
    
    return [p[offset:] for p in glob.iglob(absPath)]
      
  def copyFile(self, source, target, onlyNewer=True):
    """Copy a file from one location to another.
    
    @param source: The path of the source file or a FileTarget
    representing a file that will be created.
    @type source: string or L{FileTarget}
    
    @param target: The path of the target file to copy to
    @type target: string
    
    @param onlyNewer: Only copy source file if it's newer than the target.
    If False then always copies the file.
    @type onlyNewer: bool
    
    @return: A FileTarget representing the file that will be copied.
    @rtype: L{FileTarget}
    """
    if not isinstance(target, basestring):
      raise TypeError("target must be a string")
    
    basePath = self.configuration.basePath
    
    source = basePath(source)
    target = basePath(target)
    
    return self._copyFile(source, target, onlyNewer)
  
  def _copyFile(self, source, target, onlyNewer=True):
    
    def doCopy():
      
      sourcePath = getPath(source)
      abspath = self.configuration.abspath
      engine = self.engine
      
      targetAbsPath = abspath(target)
      sourceAbsPath = abspath(sourcePath) 
      
      if engine.forceBuild:
        reasonToBuild = "rebuild has been forced"
      elif not onlyNewer:
        reasonToBuild = "onlyNewer is False"
      elif not cake.filesys.isFile(targetAbsPath):
        reasonToBuild = "it doesn't exist"
      elif engine.getTimestamp(sourceAbsPath) > engine.getTimestamp(targetAbsPath):
        reasonToBuild = "'%s' has been changed" % sourcePath
      else:
        # up-to-date
        return

      engine.logger.outputDebug(
        "reason",
        "Rebuilding '%s' because %s.\n" % (target, reasonToBuild),
        )
      engine.logger.outputInfo("Copying %s to %s\n" % (sourcePath, target))
      
      try:
        cake.filesys.makeDirs(cake.path.dirName(targetAbsPath))
        cake.filesys.copyFile(sourceAbsPath, targetAbsPath)
      except EnvironmentError, e:
        engine.raiseError("%s: %s\n" % (target, str(e)), targets=[target])

      engine.notifyFileChanged(targetAbsPath)
    
    @waitForAsyncResult
    def run(source):
      if self.enabled:  
        sourceTask = getTask(source)
        copyTask = self.engine.createTask(doCopy)
        copyTask.lazyStartAfter(sourceTask)
      else:
        copyTask = None

      fileTarget = FileTarget(path=target, task=copyTask)

      currentScript = Script.getCurrent()
      currentScript.getDefaultTarget().addTarget(fileTarget)

      return fileTarget

    return run(source)

  def copyFiles(self, sources, targetDir):
    """Copy a collection of files to a target directory.
    
    @param sources: A list of files to copy.
    @type sources: list of string's, FileTargets or AsyncResult yielding
    a string, FileTarget or list of same.
    @param targetDir: The target directory to copy to.
    @type targetDir: string
    
    @return: A list of FileTarget's representing the files that will be
    copied.
    @rtype: list of L{FileTarget}
    """
    if not isinstance(targetDir, basestring):
      raise TypeError("targetDir must be a string")
    
    basePath = self.configuration.basePath
    
    sources = basePath(sources)
    targetDir = basePath(targetDir)
    
    @waitForAsyncResult
    def run(sources):
      results = []
      for s in sources:
        sourcePath = getPath(s)
        target = cake.path.join(targetDir, cake.path.baseName(sourcePath))
        results.append(self._copyFile(source=s, target=target))
      return results
    
    return run(flatten(sources))

  def copyDirectory(
    self,
    sourceDir,
    targetDir,
    recursive=True,
    onlyNewer=True,
    removeStale=False,
    includeMatch=None,
    ):
    """Copy the contents of a source directory to a target directory.
    
    If the target directory does not exist it will be created.
    
    @param sourceDir: The name of the source directory to copy from.
    @type sourceDir: string
    
    @param targetDir: The name of the target directory to copy to.
    @type targetDir: string
    
    @param recursive: Whether or not to copy recursively.
    @type recursive: bool
    
    @param onlyNewer: Only copy files that are newer than those in
    the target directory.
    @type onlyNewer: bool
    
    @param removeStale: Remove files and directories in the target
    directory that no longer exist in the source directory.
    @type removeStale: bool 
    
    @param includeMatch: A callable used to decide whether to include
    certain files when copying. This could be a python callable that
    returns True to copy the file or False to exclude it, or a regular
    expression function such as re.compile().match or re.match.
    @type includeMatch: any callable 
    
    @return: A list of FileTarget's representing the files that will be
    copied.
    @rtype: list of L{FileTarget}
    """
    if not isinstance(targetDir, basestring):
      raise TypeError("targetDir must be a string")
    
    basePath = self.configuration.basePath
    abspath = self.configuration.abspath
    engine = self.engine
    
    sourceDir = basePath(sourceDir)
    targetDir = basePath(targetDir)
    
    def doMakeDir(path):
      targetAbsPath = abspath(path)
      if cake.path.isDir(targetAbsPath):
        return # Don't create if it already exists.
      
      engine.logger.outputInfo("Creating Directory %s\n" % path)
      try:
        cake.filesys.makeDirs(targetAbsPath)
      except EnvironmentError, e:
        engine.raiseError("%s: %s\n" % (targetDir, str(e)))

    def doDelete(paths):
      for path in paths:
        targetPath = cake.path.join(targetDir, path)
        absTargetPath = abspath(targetPath)
        engine.logger.outputInfo("Deleting %s\n" % targetPath)
        if cake.path.isDir(absTargetPath):
          cake.filesys.removeTree(absTargetPath)
        elif cake.path.isFile(absTargetPath):
          cake.filesys.remove(absTargetPath)
        else:
          pass # Skip files that may have been deleted already due to iteration order.
    
    @waitForAsyncResult
    def run(sourceDir):
      sources = set(cake.filesys.walkTree(
        path=abspath(sourceDir),
        recursive=recursive,
        includeMatch=includeMatch,
        ))
        
      if removeStale:
        targets = set(cake.filesys.walkTree(path=abspath(targetDir), recursive=recursive))
        oldFiles = targets.difference(sources)
        removeTask = self.engine.createTask(lambda f=oldFiles: doDelete(f))
        removeTask.lazyStart()
      else:
        removeTask = None
      
      results = []
      for source in sources:
        sourcePath = cake.path.join(sourceDir, source)
        targetPath = cake.path.join(targetDir, source)
        if cake.path.isDir(abspath(sourcePath)):
          if self.enabled:  
            dirTask = self.engine.createTask(lambda t=targetPath: doMakeDir(t))
            dirTask.completeAfter(removeTask)
            dirTask.lazyStart()
          else:
            dirTask = None
          results.append(DirectoryTarget(path=source, task=dirTask))
        else:
          fileTarget = self._copyFile(source=sourcePath, target=targetPath, onlyNewer=onlyNewer)
          if fileTarget.task:
            fileTarget.task.completeAfter(removeTask)
          results.append(fileTarget)

      Script.getCurrent().getDefaultTarget().addTargets(results)

      return results
    
    return run(sourceDir)
