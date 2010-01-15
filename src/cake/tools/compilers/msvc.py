__all__ = ["MsvcCompiler"]

import cake.filesys
import cake.path
from cake.tools.compilers import Compiler, makeCommand
from cake.tools import memoise

class MsvcCompiler(Compiler):
  
  objectSuffix = '.obj'
  librarySuffix = '.lib'
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  outputFullPath = True
  memoryLimit = None
  runtimeLibraries = None
  
  def __init__(self,
    clExe=None,
    libExe=None,
    linkExe=None,
    ):
    super(MsvcCompiler, self).__init__()
    self.__clExe = clExe
    self.__libExe = libExe
    self.__linkExe = linkExe
    
  @memoise
  def _getCommonArgs(self):
    args = [
      self.__clExe,
      "/nologo",
      ]
    
    if self.outputFullPath:
      args.append("/FC")

    if self.memoryLimit is not None:
      args.append("/Zm%i" % self.memoryLimit)

    if self.debugSymbols:
      args.append("/Z7") # Embed debug info in .obj
 
    if self.runtimeLibraries == 'release-dll':
      args.append("/MD")
    elif self.runtimeLibraries == 'debug-dll':
      args.append("/MDd")
    elif self.runtimeLibraries == 'release-static':
      args.append("/MT")
    elif self.runtimeLibraries == 'debug-static':
      args.append("/MTd")
 
    return args 
    
  @memoise
  def _getPreprocessorCommonArgs(self):
    args = list(self._getCommonArgs())
   
    for define in self.defines:
      args.append("/D%s" % define)
      
    for includePath in self.includePaths:
      args.append("/I%s" % includePath)

    args.append("/E")
    
    return args
    
  @memoise
  def _getCompileCommonArgs(self):
    args = list(self._getCommonArgs())
    args.append("/c")
    return args
    
  def getObjectCommands(self, target, source, engine):
    
    if source.lower().endswith('.c'):
      language = 'C'
    else:
      language = 'C++'
    
    preprocessTarget = target + '.i'
    
    compileArgs = self._getCompileCommonArgs()
    compileArgs.extend([preprocessTarget, "/Fo" + target])
    
    preprocessArgs = self._getPreprocessorCommonArgs()
    if language == 'C':
      preprocessArgs.append('/Tc' + source)
    else:
      preprocessArgs.append('/Tp' + source)
    
    @makeCommand(preprocessArgs)
    def preprocess():
      engine.logger.outputInfo("running: %s" % " ".join(preprocessArgs))

    @makeCommand("msvc-scan")
    def scan():
      engine.logger.outputInfo("scanning: %s" % preprocessTarget)
      return [source]
    
    @makeCommand(compileArgs)
    def compile():
      engine.logger.outputInfo("running: %s" % " ".join(compileArgs))
      cake.filesys.makeDirs(cake.path.directory(target))
      with open(target, 'wb'):
        pass

    return preprocess, scan, compile
