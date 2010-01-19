__all__ = ["MsvcCompiler"]

import os
import os.path
import subprocess
import tempfile
import re
import threading

import cake.filesys
import cake.path
from cake.tools.compilers import Compiler, makeCommand
from cake.tools import memoise
from cake.task import Task

class MsvcCompiler(Compiler):

  _lineRegex = re.compile('#line [0-9]+ "(?P<path>.+)"', re.MULTILINE)
  _pdbQueue = {}
  _pdbQueueLock = threading.Lock()
  
  objectSuffix = '.obj'
  librarySuffix = '.lib'
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  outputFullPath = True
  memoryLimit = None
  runtimeLibraries = None
  useFunctionLevelLinking = False
  useStringPooling = False
  useMinimalRebuild = False
  useEditAndContinue = False
  
  errorReport = 'queue'
  
  pdbFile = None
  
  def __init__(
    self,
    clExe=None,
    libExe=None,
    linkExe=None,
    dllPaths=None,
    architecture=None,
    ):
    super(MsvcCompiler, self).__init__()
    self.__clExe = clExe
    self.__libExe = libExe
    self.__linkExe = linkExe
    self.__dllPaths = dllPaths
    
  @memoise
  def _getCommonArgs(self, language):
    args = [
      os.path.basename(self.__clExe),
      "/nologo",
      ]
    
    if self.outputFullPath:
      args.append("/FC")

    if self.memoryLimit is not None:
      args.append("/Zm%i" % self.memoryLimit)

    if self.runtimeLibraries == 'release-dll':
      args.append("/MD")
    elif self.runtimeLibraries == 'debug-dll':
      args.append("/MDd")
    elif self.runtimeLibraries == 'release-static':
      args.append("/MT")
    elif self.runtimeLibraries == 'debug-static':
      args.append("/MTd")
 
    if self.useFunctionLevelLinking:
      args.append('/Gy') # Enable function-level linking
 
    if self.useStringPooling:
      args.append('/GF') # Eliminate duplicate strings
 
    if language == 'C++':
      if self.enableRtti:
        args.append('/GR') # Enable RTTI
      else:
        args.append('/GR-') # Disable RTTI
      
      if self.enableExceptions == "SEH":
        args.append('/EHa') # Enable SEH exceptions
      elif self.enableExceptions:
        args.append('/EHsc') # Enable exceptions
      else:
        args.append('/EHsc-') # Disable exceptions
 
    if self.warningLevel is not None:
      args.append('/W%s' % self.warningLevel)
      
    if self.warningsAsErrors:
      args.append('/WX')
 
    if self.errorReport:
      args.append('/errorReport:' + self.errorReport)
 
    return args 
    
  @memoise
  def _getPreprocessorCommonArgs(self, language):
    args = list(self._getCommonArgs(language))
   
    args.extend("/D" + define for define in self.defines)
    args.extend("/I" + path for path in self.includePaths)
    args.extend("/FI" + path for path in self.forceIncludes)

    args.append("/E")
    
    return args
    
  @property
  @memoise
  def _needPdbFile(self):
    if self.pdbFile is not None and self.debugSymbols:
      return True
    elif self.useMinimalRebuild or self.useEditAndContinue:
      return True
    else:
      return False
    
  @memoise
  def _getCompileCommonArgs(self, language):
    args = list(self._getCommonArgs(language))

    if self.useEditAndContinue:
      args.append("/ZI") # Output debug info to PDB (edit-and-continue)
    elif self._needPdbFile:
      args.append("/Zi") # Output debug info to PDB (no edit-and-continue)
    elif self.debugSymbols:
      args.append("/Z7") # Output debug info embedded in .obj
    
    if self.useMinimalRebuild:
      args.append("/Gm") # Enable minimal rebuild
    
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
    compileArgs = list(self._getCompileCommonArgs(language))
    preprocessArgs = list(self._getPreprocessorCommonArgs(language))
    
    if language == 'C':
      preprocessArgs.append('/Tc' + source)
      compileArgs.append('/Tc' + preprocessTarget)
    else:
      preprocessArgs.append('/Tp' + source)
      compileArgs.append('/Tp' + preprocessTarget)

    if self._needPdbFile:
      pdbFile = self.pdbFile if self.pdbFile is not None else target + '.pdb'
      compileArgs.append('/Fd' + pdbFile)
    else:
      pdbFile = None

    compileArgs.append('/Fo' + target)
    
    preprocessorOutput = []
    
    @makeCommand(preprocessArgs + ['>', preprocessTarget])
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
      # TODO: Add dependencies on DLLs used by cl.exe
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
      
    @makeCommand(compileArgs)
    def compileWhenPdbIsFree():
      with self._pdbQueueLock:
        predecessor = self._pdbQueue.get(pdbFile, None)
        if predecessor is None or predecessor.completed:
          # No prior compiles using this .pdb can start this
          # one immediately in the same task.
          compileTask = Task.getCurrent()
          compileNow = True
        else:
          # Another compile task is using this .pdb
          # We'll start after it finishes
          compileTask = engine.createTask(compile)
          predecessor.addCallback(compileTask.start)
          compileNow = False
        self._pdbQueue[pdbFile] = compileTask
        
      if compileNow:
        compile()
      
    if pdbFile is not None:
      # Debug info is embedded in the .pdb so we can't cache the
      # object file without somehow pulling the .pdb along for
      # the ride.
      canBeCached = False
      return preprocess, scan, compileWhenPdbIsFree, canBeCached 
    else:
      # Debug info is embedded in the .obj so we can cache the
      # object file without losing debug info.
      canBeCached = True
      return preprocess, scan, compile, canBeCached

  @memoise
  def _getCommonLibraryArgs(self):
    args = [cake.path.baseName(self.__libExe), '/nologo']
    
    # XXX: MSDN says /errorReport:queue is supported by lib.exe
    # but it seems to go unrecognised in MSVC8.
    #if self.errorReport:
    #  args.append('/ERRORREPORT:' + self.errorReport.upper())

    if self.optimisation == self.FULL_OPTIMISATION:
      args.append('/LTCG')

    if self.warningsAsErrors:
      args.append('/WX')
    else:
      args.append('/WX:NO')

    return args

  def getLibraryCommand(self, target, sources, engine):
    
    args = list(self._getCommonLibraryArgs())

    args.append('/OUT:' + target)
    
    args.extend(sources)
    
    @makeCommand(args)
    def archive():

      engine.logger.outputInfo("run: %s\n" % " ".join(args))
      
      argsFile = target + '.args' 
      with open(argsFile, 'wt') as f:
        for arg in args[1:]:
          f.write(arg + '\n')

      try:
        p = subprocess.Popen(
          args=[args[0], '@' + argsFile],
          executable=self.__libExe,
          env=self._getProcessEnv(),
          stdin=subprocess.PIPE,
          stdout=subprocess.PIPE,
          stderr=subprocess.STDOUT,
          )
      except EnvironmentError, e:
        engine.raiseError("cake: failed to launch %s: %s" % (self.__libExe, str(e)))
    
      p.stdin.close()
      output = p.stdout.read()
      exitCode = p.wait()
    
      for line in output:
        if not line.rstrip():
          continue
        if 'error' in line:
          engine.logger.outputError(line)
        elif 'warning' in line:
          engine.logger.outputWarning(line)
        else:
          engine.logger.outputInfo(line)
          
      if exitCode != 0:
        engine.raiseError("lib: failed with exit code %i" % exitCode)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by lib.exe
      return [self.__libExe] + sources

    return archive, scan
