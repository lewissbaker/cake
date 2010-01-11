
__all__ = ["DummyCompiler"]

import os.path

import cake.path
import cake.filesys

from cake.tools.compilers import Compiler
from cake.tools import FileTarget, getPathsAndTasks, getPathAndTask
from cake.task import Task
from cake.engine import Script, DependencyInfo, FileInfo

class DummyCompiler(Compiler):
  
  def __init__(self):
    Compiler.__init__(self)

  def object(self, target, source, forceExtension=True):
    compiler = self.clone()
    engine = Script.getCurrent().engine
    
    def run():
      commandLine = ["gcc", "/c", sourcePath, "/o", target]
      if compiler.useDebugSymbols:
        commandLine.append("/debug")

      # Check if the object file needs building
      oldDependencyInfo = None
      if os.path.isfile(target):
        try:
          oldDependencyInfo = engine.getDependencyInfo(target)
          if oldDependencyInfo.args == commandLine:
            for dependency in oldDependencyInfo.dependencies:
              if dependency.hasChanged(engine):
                print "Object %s building because %s changed." % (target, dependency.path)
                break
            else:
              print "Object %s is up to date." % target
              return
          else:
            print "Object %s building because command-line changed." % target
        except EnvironmentError:
          print "Object %s building because dependency file is missing." % target
      else:
        print "Object %s building because it doesn't exist." % target

      # Ok, if we get to here then we know the target is out of date.
      # First we check if we can retrieve a prebuilt version from the
      # cache. 

      def preprocess():
        print "Object %s preprocessing..." % target
        
      def dependencyScan(dependencies):
        print "Object %s scanning for dependencies..." % target 
        dependencies.append(sourcePath)

      def compile():
        print "Object %s compiling..." % target
        cake.filesys.makeDirs(cake.path.directory(target))
        with open(target, 'wb'):
          pass
        
      def storeDependencyInfo(dependencyInfo):
        print "Object %s storing dependency info..." % target
        engine.storeDependencyInfo(dependencyInfo)

      # XXX: Should these vars be members of the Engine or Compiler classes?
      useBuildCache = True
      buildCachePath = "c:\\build-cache"
      def getCacheEntryPath(digest):
        digestStr = "".join("%02x" % ord(c) for c in digest)
        return os.path.join(buildCachePath, digestStr[0], digestStr[1], digestStr)

      if useBuildCache:
        #
        # Build logic using an object cache
        #
        
        if oldDependencyInfo is not None:
          newDependencyInfo = DependencyInfo(
            targets=[FileInfo(path=target)],
            args=commandLine,
            dependencies=oldDependencyInfo.dependencies,
            )
        
          newDigest = newDependencyInfo.calculateDigest(engine)
          
          # Lookup entry in build cache
          cacheEntryPath = getCacheEntryPath(newDigest)
          if os.path.isfile(cacheEntryPath):
            print "Object %s being copied from cache" % target
            cake.filesys.copyFile(cacheEntryPath, target)
            engine.storeDependencyInfo(newDependencyInfo)
            return
          
        # Execute preprocessor
        preprocess()
        
        # Execute dependency scanner
        dependencies = []
        dependencyScan(dependencies)
        
        newDependencyInfo = DependencyInfo(
          targets=[FileInfo(path=target)],
          args=commandLine,
          dependencies=[
            FileInfo(
              path=path,
              timestamp=engine.getTimestamp(path),
              digest=engine.getFileDigest(path),
              )
            for path in dependencies
            ]
          )
      
        # TODO: Could avoid second digest calculation if dependencies
        # haven't changed.
        newDigest = newDependencyInfo.calculateDigest(engine)
        
        # Lookup entry in build cache
        cacheEntryPath = getCacheEntryPath(newDigest)
        if os.path.isfile(cacheEntryPath):
          print "Object %s being copied from cache" % target
          cake.filesys.copyFile(cacheEntryPath, target)
          engine.storeDependencyInfo(newDependencyInfo)
          return
        
        # Perform compilation
        compile()

        storeDependencyInfo(newDependencyInfo)
        
        # Copy compiled file to cache
        try:
          cake.filesys.makeDirs(cake.path.directory(cacheEntryPath))
          cake.filesys.copyFile(target, cacheEntryPath)
        except EnvironmentError:
          # Don't sweat if we couldn't copy to the cache
          pass
        
      else:
        #
        # Build logic without use of object cache
        #

        preprocess()

        dependencies = []
        scanTask = Task(lambda d=dependencies: dependencyScan(dependencies))
        scanTask.start()

        compileTask = Task(compile)
        compileTask.start()
        
        storeDepTask = Task(
          lambda:
            storeDependencyInfo(
              DependencyInfo(
                targets=[FileInfo(path=target)],
                args=commandLine,
                dependencies=[
                  FileInfo(
                    path=path,
                    timestamp=engine.getTimestamp(),
                    )
                  for path in dependencies
                  ],
                )
              )
            )
        storeDepTask.startAfter([scanTask, compileTask])

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
