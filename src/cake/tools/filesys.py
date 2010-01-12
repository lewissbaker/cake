import cake.engine
import cake.path
import cake.filesys
from cake.tools import FileTarget, getPathAndTask

class FileSystemTool(cake.engine.Tool):
  
  def __init__(self):
    pass

  def cwd(self, *args):
    """Return the path prefixed with the current script's directory.
    """
    script = cake.engine.Script.getCurrent()
    return script.cwd(*args)

  def copyFile(self, source, target):
    """Copy a file from one location to another.
    
    @param source: The path of the source file or a FileTarget
    representing a file that will be created.
    @type source: string or FileTarget
    
    @param target: The path of the target file to copy to
    @type target: string
    
    @return: A FileTarget representing the file that will be copied.
    """
    if not isinstance(target, basestring):
      raise TypeError("target must be a string")
    
    sourcePath, sourceTask = getPathAndTask(source)
   
    engine = cake.engine.Script.getCurrent().engine
   
    def doCopy():
      if cake.filesys.isFile(target) and \
         engine.getTimestamp(sourcePath) <= engine.getTimestamp(target):
        # up-to-date
        return
      
      print "Copying %s to %s" % (sourcePath, target)
      cake.filesys.makeDirs(cake.path.directory(target))
      cake.filesys.copyFile(sourcePath, target)
      engine.notifyFileChanged(target)
      
    copyTask = cake.task.Task(doCopy)
    copyTask.startAfter(sourceTask)

    return FileTarget(path=target, task=copyTask)

  def copyFiles(self, sources, target):
    """Copy a collection of files to a target directory.
    """
    raise NotImplementedError()
  
  def copyDirectory(self, source, target, pattern=None):
    """Copy the directory's contents to the target directory,
    creating the target directory if needed.
    """
    raise NotImplementedError()
  
  