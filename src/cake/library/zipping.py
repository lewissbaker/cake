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
    includes=None,
    excludes=None,
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
    @param includes: A list of include expressions used to include certain
    files in the extraction. These could be regular expression objects
    returned by re.compile(), or simply an object that exposes a
    match(string) function.
    @type includes: list of obj.match(string) 
    @param excludes: A list of exclude expressions used to exclude certain
    files from being extracted. These could be regular expression objects
    returned by re.compile(), or simply an object that exposes a
    match(string) function.
    @type exclude: list of obj.match(string)
    
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
        
        if includes is not None:
          newZipInfos = []
          for zipInfo in zipInfos:
            for expression in includes:
              if expression.match(zipInfo.filename):
                newZipInfos.append(zipInfo)
                break
          zipInfos = newZipInfos

        if excludes is not None:
          newZipInfos = []
          for zipInfo in zipInfos:
            for expression in excludes:
              if expression.match(zipInfo.filename):
                break
            else:
              newZipInfos.append(zipInfo)
          zipInfos = newZipInfos
        
        if removeStale:
          zipFiles = []
          for zipInfo in zipInfos:
            path = os.path.join(targetDir, zipInfo.filename)
            zipFiles.append(os.path.normpath(os.path.normcase(path)))
          
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
