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
    includeFunc=None,
    excludeFunc=None,
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
    @param includeFunc: A callable used to decide whether to include
    certain files in the extraction. This could be a python callable that
    returns True to include the file or False to exclude it, or a regular
    expression function such as re.compile().match or re.match.
    @type includeFunc: any callable 
    @param excludeFunc: A callable used to decide whether to exclude certain
    files from being extracted. This could be a python callable that
    returns True to exclude the file or False to include it, or a regular
    expression function such as re.compile().match or re.match.
    @type excludeFunc: any callable 
    
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
        
        if includeFunc is not None:
          newZipInfos = []
          for zipInfo in zipInfos:
            if includeFunc(zipInfo.filename):
              newZipInfos.append(zipInfo)
          zipInfos = newZipInfos

        if excludeFunc is not None:
          newZipInfos = []
          for zipInfo in zipInfos:
            if not excludeFunc(zipInfo.filename):
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
