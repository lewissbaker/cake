__all__ = ["MsvcCompiler"]

import os
import os.path
import subprocess
import tempfile
import re

import cake.filesys
import cake.path
from cake.tools.compilers import Compiler, makeCommand
from cake.tools import memoise

class MsvcCompiler(Compiler):

  _lineRegex = re.compile('#line [0-9]+ "(?P<path>.+)"', re.MULTILINE)
  
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
    dllPaths=None,
    ):
    super(MsvcCompiler, self).__init__()
    self.__clExe = clExe
    self.__libExe = libExe
    self.__linkExe = linkExe
    self.__dllPaths = dllPaths
    
  @memoise
  def _getCommonArgs(self):
    args = [
      os.path.basename(self.__clExe),
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
    
  @memoise
  def _getProcessEnv(self):
    temp = os.environ.get('TMP', os.environ.get('TEMP', os.getcwd()))
    env = {
      'COMPSPEC' : os.environ.get('COMSPEC', ''),
      'PATHEXT' : ".com;.exe;.bat;.cmd",
      'SYSTEMROOT' : os.environ.get('SYSTEMROOT', ''),
      'TMP' : temp,
      'TEMP' : temp,  
      'PATH' : '.',
      }
    if self.__dllPaths is not None:
      env['PATH'] = os.path.pathsep.join(
        [env['PATH']] + self.__dllPaths
        )
    
    if env['SYSTEMROOT']:
      env['PATH'] = os.path.pathsep.join([
        env['PATH'],
        os.path.join(env['SYSTEMROOT'], 'System32'),
        env['SYSTEMROOT'],
        ])
      
    return env
    
  def getObjectCommands(self, target, source, engine):
    
    if source.lower().endswith('.c'):
      language = 'C'
    else:
      language = 'C++'
    
    preprocessTarget = target + '.i'

    processEnv = dict(self._getProcessEnv())    

    compileArgs = list(self._getCompileCommonArgs())
    
    preprocessArgs = list(self._getPreprocessorCommonArgs())
    if language == 'C':
      preprocessArgs.append('/Tc' + source)
      compileArgs.append('/Tc' + preprocessTarget)
    else:
      preprocessArgs.append('/Tp' + source)
      compileArgs.append('/Tp' + preprocessTarget)

    compileArgs.append('/Fo' + target)
    
    preprocessorOutput = [] 
    
    @makeCommand(preprocessArgs)
    def preprocess():
      engine.logger.outputInfo("run: %s\n" % " ".join(preprocessArgs))
      
      with tempfile.TemporaryFile() as errFile:
        # Launch the process
        try:
          p = subprocess.Popen(
            args=preprocessArgs,
            executable=self.__clExe,
            env=processEnv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=errFile,
            )
        except EnvironmentError, e:
          engine.raiseError("cake: failed to launch %s: %s\n" % (self.__clExe, str(e)))
        p.stdin.close()
        
        output = p.stdout.read()
        exitCode = p.wait()
        
        sourceName = cake.path.baseName(source)
        
        errFile.seek(0)
        for line in errFile:
          line = line.rstrip()
          if not line or line == sourceName:
            continue
          if 'error' in line:
            engine.logger.outputError(line)
          elif 'warning' in line:
            engine.logger.outputWarning(line)
          else:
            engine.logger.outputInfo(line)

        if exitCode != 0:
          raise engine.raiseError("cl: failed with exit code %i\n" % exitCode)

      cake.filesys.makeDirs(cake.path.directory(preprocessTarget))
      with open(preprocessTarget, 'wb') as f:
        f.write(output)

      preprocessorOutput.append(output)

    @makeCommand("msvc-scan")
    def scan():
      engine.logger.outputInfo("scan: %s\n" % preprocessTarget)
      dependencies = [self.__clExe]
      uniqueDeps = set()
      for match in self._lineRegex.finditer(preprocessorOutput[0]):
        path = match.group('path').replace('\\\\', '\\')
        if path not in uniqueDeps:
          uniqueDeps.add(path)
          dependencies.append(path)
      return dependencies
    
    @makeCommand(compileArgs)
    def compile():
      engine.logger.outputInfo("run: %s\n" % " ".join(compileArgs))
      cake.filesys.makeDirs(cake.path.directory(target))
      
      with tempfile.TemporaryFile() as errFile:
        try:
          p = subprocess.Popen(
            args=compileArgs,
            executable=self.__clExe,
            env=processEnv,
            stdin=subprocess.PIPE,
            stdout=errFile,
            stderr=subprocess.STDOUT,
            )
        except EnvironmentError, e:
          engine.raiseError("cake: failed to run %s: %s" % (self.__clExe, str(e)))
          
        p.stdin.close()
        
        exitCode = p.wait()
        
        sourceName = cake.path.baseName(preprocessTarget)
        
        errFile.seek(0)
        for line in errFile:
          line = line.rstrip()
          if not line or line == sourceName:
            continue
          if 'error' in line:
            engine.logger.outputError(line)
          elif 'warning' in line:
            engine.logger.outputError(line)
          else: 
            engine.logger.outputInfo(line)
        
        if exitCode != 0:
          engine.raiseError("cl: failed with code %i" % exitCode)
      
    return preprocess, scan, compile
