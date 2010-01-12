
__all__ = ["DummyCompiler"]

import cake.filesys
import cake.path
from cake.tools.compilers import Compiler

class DummyCommand(object):
  
  def __init__(self, name, func):
    self.name = name
    self.func = func
    
  def __repr__(self):
    return repr(self.name)
  
  def __call__(self):
    return self.func()

def makeCommand(name):
  def run(func):
    return DummyCommand(name, func)
  return run

class DummyCompiler(Compiler):
  
  objectSuffix = '.obj'
  librarySuffix = '.lib'
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  def __init__(self):
    Compiler.__init__(self)

  def getObjectCommands(self, target, source):
    
    preprocessTarget = target + ".i"
    
    @makeCommand(["gcc", "/e", source, "/o", preprocessTarget])
    def preprocess():
      print "Preprocessing %s" % source
      cake.filesys.makeDirs(cake.path.directory(preprocessTarget))
      with open(preprocessTarget, 'wb'):
        pass

    @makeCommand("dummy-scan")
    def scan():
      print "Scanning %s" % source
      return [source]
    
    @makeCommand(["gcc", "/c", preprocessTarget, "/o", target])
    def compile():
      print "Compiling %s" % source
      cake.filesys.makeDirs(cake.path.directory(target))
      with open(target, 'wb'):
        pass

    return preprocess, scan, compile
