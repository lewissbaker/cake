"""File System Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import cake.path
import cake.filesys
from cake.library import Tool, FileTarget, getPathAndTask

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
    
    sourcePath, sourceTask = getPathAndTask(source)
   
    def doCopy():
      
      abspath = self.configuration.abspath
      engine = self.engine
      
      targetAbsPath = abspath(target)
      sourceAbsPath = abspath(sourcePath) 
      
      if engine.forceBuild:
        reasonToBuild = "rebuild has been forced"
      elif not cake.filesys.isFile(targetAbsPath):
        reasonToBuild = "'%s' does not exist" % target
      elif engine.getTimestamp(sourceAbsPath) > engine.getTimestamp(targetAbsPath):
        reasonToBuild = "'%s' is newer than '%s'" % (sourcePath, target)
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
      
    copyTask = self.engine.createTask(doCopy)
    copyTask.startAfter(sourceTask)

    return FileTarget(path=target, task=copyTask)

  def copyFiles(self, sources, targetDir):
    """Copy a collection of files to a target directory.
    
    @param sources: A list of files to copy.
    @type sources: list of string's
    @param targetDir: The target directory to copy to.
    @type targetDir: string
    
    @return: A list of FileTarget's representing the files that will be
    copied.
    @rtype: list of L{FileTarget}
    """
    if not isinstance(targetDir, basestring):
      raise TypeError("targetDir must be a string")
    
    results = []
    for s in sources:
      sourcePath, _ = getPathAndTask(s)
      target = cake.path.join(targetDir, cake.path.baseName(sourcePath))
      results.append(self.copyFile(source=s, target=target))
    return results
  
  def copyDirectory(self, source, target, pattern=None):
    """Copy the directory's contents to the target directory,
    creating the target directory if needed.

    Not yet Implemented!
    """
    raise NotImplementedError()
  
  