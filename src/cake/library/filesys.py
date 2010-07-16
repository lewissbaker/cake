"""File System Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import cake.path
import cake.filesys
from cake.library import Tool, FileTarget, getPath, getTask, \
                         flatten, waitForAsyncResult

class FileSystemTool(Tool):
  """Tool that provides file system related utilities. 
  """

  def copyFile(self, source, target):
    """Copy a file from one location to another.
    
    @param source: The path of the source file or a FileTarget
    representing a file that will be created.
    @type source: string or L{FileTarget}
    
    @param target: The path of the target file to copy to
    @type target: string
    
    @return: A FileTarget representing the file that will be copied.
    @rtype: L{FileTarget}
    """
    if not isinstance(target, basestring):
      raise TypeError("target must be a string")
    
    def doCopy():
      
      sourcePath = getPath(source)
      abspath = self.configuration.abspath
      engine = self.engine
      
      targetAbsPath = abspath(target)
      sourceAbsPath = abspath(sourcePath) 
      
      if engine.forceBuild:
        reasonToBuild = "rebuild has been forced"
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
        engine.raiseError("%s: %s\n" % (target, str(e)))

      engine.notifyFileChanged(targetAbsPath)
    
    @waitForAsyncResult
    def run(source):
      if self.enabled:  
        sourceTask = getTask(source)
        copyTask = self.engine.createTask(doCopy)
        copyTask.startAfter(sourceTask)
      else:
        copyTask = None

      return FileTarget(path=target, task=copyTask)

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
    
    @waitForAsyncResult
    def run(sources):
      results = []
      for s in sources:
        sourcePath = getPath(s)
        target = cake.path.join(targetDir, cake.path.baseName(sourcePath))
        results.append(self.copyFile(source=s, target=target))
      return results
    
    return run(flatten(sources))

  
  