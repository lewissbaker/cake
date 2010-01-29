
__all__ = ["DummyCompiler"]

import cake.filesys
import cake.path
from cake.tools.compilers import Compiler, makeCommand

class DummyCompiler(Compiler):
  
  objectSuffix = '.obj'
  librarySuffix = '.lib'
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  def __init__(self):
    Compiler.__init__(self)

  def getObjectCommands(self, target, source, engine):

    canBeCached = True

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
    def preprocess():
      print "Preprocessing %s" % source
      cake.filesys.makeDirs(cake.path.dirName(preprocessTarget))
      with open(preprocessTarget, 'wb'):
        pass

    @makeCommand("dummy-scan")
    def scan():
      print "Scanning %s" % source
      return [source]
    
    @makeCommand(compilerArgs + [preprocessTarget, "/o", target])
    def compile():
      print "Compiling %s" % source
      cake.filesys.makeDirs(cake.path.dirName(target))
      with open(target, 'wb'):
        pass

    return preprocess, scan, compile, canBeCached
