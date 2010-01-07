
__all__ = ["DummyCompiler"]

import cake.path

from cake.tools.compilers import Compiler
from cake.tools import FileTarget, getPathsAndTasks, getPathAndTask
from cake.task import Task
from cake.engine import Script

class DummyCompiler(Compiler):
  
  def __init__(self):
    Compiler.__init__(self)

  def object(self, target, source, forceExtension=True):
    
    def run():
      print "Compiling object %s from %s" % (target, sourcePath)
      cake.filesys.makeDirs(cake.path.directory(target))
      with open(target, 'w'):
        pass
    
    if forceExtension:
      target = cake.path.forceExtension(target, ".obj")
      
    sourcePath, sourceTask = getPathAndTask(source)
    
    task = Task(run)
    task.startAfter(sourceTask)
    
    return FileTarget(path=target, task=task)
    
  def objects(self, target, sources):
    results = []
    for source in sources:
      sourcePath, _ = getPathAndTask(source)
      sourceName = cake.path.baseNameWithoutExtension(sourcePath)
      targetPath = cake.path.join(target, sourceName)
      results.append(self.object(targetPath, source))
    return results
    
  def library(self, target, sources, forceExtension=True):
    def run():
      print "Archiving library %s" % target
      with open(target, 'w'):
        pass

    if forceExtension:
      target = cake.path.forceExtension(target, ".lib")
      
    paths, tasks = getPathsAndTasks(sources)
    
    task = Task(run)
    task.startAfter(tasks)
    
    return FileTarget(path=target, task=task)
    
  def module(self, target, sources, forceExtension=True):
    def run():
      print "Linking module %s" % target
      with open(target, 'w'):
        pass

    if forceExtension:
      target = cake.path.forceExtension(target, ".dll")
      
    paths, tasks = getPathsAndTasks(sources)
      
    task = Task(run)
    task.startAfter(tasks)
    
    return FileTarget(path=target, task=task)
    
  def executable(self, target, sources, forceExtension=True):
    def run():
      print "Linking executable %s" % target
      with open(target, 'w'):
        pass
      
    if forceExtension:
      target = cake.path.forceExtension(target, ".exe")
      
    paths, tasks = getPathsAndTasks(sources)
     
    task = Task(run)
    task.startAfter(tasks)

    return FileTarget(path=target, task=task)
