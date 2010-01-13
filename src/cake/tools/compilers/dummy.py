
__all__ = ["DummyCompiler"]

import cake.filesys
import cake.path
from cake.tools.compilers import Compiler

class DummyCommand(object):
  
  def __init__(self, args, func):
    self.args = args
    self.func = func
    
  def __repr__(self):
    return repr(self.args)
  
  def __call__(self, *args):
    return self.func(*args)

def makeCommand(args):
  def run(func):
    return DummyCommand(args, func)
  return run

class DummyCompiler(Compiler):
  
  objectSuffix = '.obj'
  librarySuffix = '.lib'
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  def __init__(self):
    Compiler.__init__(self)

  def getObjectCommands(self, target, source):

    preprocessorArgs = self._argsCache.get('preprocessor', None)
    compilerArgs = self._argsCache.get('compiler', None)

    if preprocessorArgs is None or compilerArgs is None:
      # calculate compiler args
      preprocessorArgs = ["gcc", "/e"]
      compilerArgs = ["gcc", "/c"]
      if self.debugSymbols:
        preprocessorArgs.append("/D=DEBUG")
        compilerArgs.append("/debug")
        
      self._argsCache['preprocessor'] = preprocessorArgs
      self._argsCache['compiler'] = compilerArgs
    
    preprocessTarget = target + ".i"
    
    @makeCommand(preprocessorArgs + [source, "/o", preprocessTarget])
    def preprocess(engine):
      print "Preprocessing %s" % source
      cake.filesys.makeDirs(cake.path.directory(preprocessTarget))
      with open(preprocessTarget, 'wb'):
        pass

    @makeCommand("dummy-scan")
    def scan(engine):
      print "Scanning %s" % source
      return [source]
    
    @makeCommand(compilerArgs + [preprocessTarget, "/o", target])
    def compile(engine):
      print "Compiling %s" % source
      cake.filesys.makeDirs(cake.path.directory(target))
      with open(target, 'wb'):
        pass

    return preprocess, scan, compile
