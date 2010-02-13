"""File System Tool.
"""

import cake.path
import cake.filesys
from cake.library import Tool, FileTarget, getPathAndTask
from cake.engine import Script

class FileSystemTool(Tool):
  """Tool that provides file system related utilities. 
  """
  
  def cwd(self, *args):
    """Return the path prefixed with the current script's directory.
    
    Examples::
      env.cwd("a") -> "{cwd}/a"
      env.cwd(["a", "b", "c"]) -> ["{cwd}/a", "{cwd}/b", "{cwd}/c"]
      
    @param args: The arguments that need to have the prefix added.
    @type args: string or list(string)
    
    @return: The path prefixed with the current script's directory.
    @rtype: string or list(string)
    """
    script = Script.getCurrent()
    return script.cwd(*args)

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
   
    engine = Script.getCurrent().engine
   
    def doCopy():
      if cake.filesys.isFile(target) and \
         engine.getTimestamp(sourcePath) <= engine.getTimestamp(target):
        # up-to-date
        return

      engine.logger.outputInfo("Copying %s to %s\n" % (sourcePath, target))
      
      try:
        cake.filesys.makeDirs(cake.path.dirName(target))
        cake.filesys.copyFile(sourcePath, target)
      except EnvironmentError, e:
        engine.raiseError("%s: %s" % (target, str(e)))

      engine.notifyFileChanged(target)
      
    copyTask = engine.createTask(doCopy)
    copyTask.startAfter(sourceTask)

    return FileTarget(path=target, task=copyTask)

  def copyFiles(self, sources, target):
    """Copy a collection of files to a target directory.
    
    Not yet Implemented!
    
    @param sources: A list of files to copy.
    @type sources: list of string's
    @param target: The target directory to copy to.
    @type target: string
    
    @return: A list of FileTarget's representing the files that will be
    copied.
    @rtype: list of L{FileTarget}
    """
    raise NotImplementedError()
  
  def copyDirectory(self, source, target, pattern=None):
    """Copy the directory's contents to the target directory,
    creating the target directory if needed.

    Not yet Implemented!
    """
    raise NotImplementedError()
  
  