"""The Metrowerks CodeWarrior Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from __future__ import with_statement

import os
import os.path
import sys
import subprocess

import cake.filesys
import cake.path
from cake.library import memoise
from cake.library.compilers import Compiler, makeCommand
from cake.gnu import parseDependencyFile

class MwcwCompiler(Compiler):

  libraryPrefixSuffixes = [('', '.a')]
  programSuffix = '.elf'

  def __init__(
    self,
    ccExe=None,
    ldExe=None,
    architecture=None,
    ):
    Compiler.__init__(self)
    self.__ccExe = ccExe
    self.__ldExe = ldExe
    self.__architecture = architecture

  @property
  def architecture(self):
    return self.__architecture
  
  @memoise
  def _getProcessEnv(self, executable):
    temp = os.environ.get('TMP', os.environ.get('TEMP', os.getcwd()))
    env = {
      'COMPSPEC' : os.environ.get('COMSPEC', ''),
      'PATHEXT' : ".com;.exe;.bat;.cmd",
      'SYSTEMROOT' : os.environ.get('SYSTEMROOT', ''),
      'TMP' : temp,
      'TEMP' : temp,  
      'PATH' : cake.path.dirName(executable),
      }
    if env['SYSTEMROOT']:
      env['PATH'] = os.path.pathsep.join([
        env['PATH'],
        os.path.join(env['SYSTEMROOT'], 'System32'),
        env['SYSTEMROOT'],
        ])
    return env

  def _formatMessage(self, inputText):
    """Format errors to be clickable in MS Visual Studio.
    """
    def readLine(text):
      res, _, text = text.partition("\r\n")
      return res, text

    line, inputText = readLine(inputText)
    outputText = ""
    indent = "   "

    while line.count("|") == 2:
      executable, component, type = line.split("|")
      line, inputText = readLine(inputText)
      
      if line.count("|") == 5:
        path, lineNum, colNum, _, _, _ = line[1:-1].split("|") 
        line, inputText = readLine(inputText)
      else:
        path = executable
        lineNum = component
        colNum = None
  
      contextLines = []
      while line.startswith("="):
        contextLines.append(line[1:])
        line, inputText = readLine(inputText)
        
      messageLines = []
      while line.startswith(">"):
        messageLines.append(line[1:])
        line, inputText = readLine(inputText)

      outputText += "%s(%s): %s: %s\n" % (
        path,
        lineNum,
        type.lower(),
        messageLines[0],
        )
      
      # Context from the offending source file
      if contextLines:
        # Write out first line with ^ underneath pointing to the offending column
        outputText += indent + contextLines[0] + "\n"
        if colNum is not None:
          outputText += indent + " " * (int(colNum) - 1) + "^\n"
    
        # Write out any remaining lines (if any)
        for line in contextLines[1:]:
          outputText += indent + line + "\n"

      if len(messageLines) > 1:
        # Write out the message again if it was multi-line
        for messageLine in messageLines:
          outputText += indent + messageLine + "\n"
    
    # Write the remaining lines
    if line:
      outputText += line + "\n"
    outputText += inputText.replace("\r", "")

    return outputText
      
  def _executeProcess(self, args, target, engine):
    engine.logger.outputDebug(
      "run",
      "run: %s\n" % " ".join(args),
      )
    cake.filesys.makeDirs(cake.path.dirName(target))

    argsFile = target + '.args'
    with open(argsFile, 'wt') as f:
      for arg in args[1:]:
        f.write('"' + arg + '"\n')

    try:
      p = subprocess.Popen(
        args=[args[0], '@' + argsFile],
        executable=args[0],
        env=self._getProcessEnv(args[0]),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        )
    except EnvironmentError, e:
      engine.raiseError(
        "cake: failed to launch %s: %s\n" % (args[0], str(e))
        )
  
    p.stdin.close()
    output = p.stdout.read()
    exitCode = p.wait()
    
    if output:
      sys.stderr.write(self._formatMessage(output))
        
    if exitCode != 0:
      engine.raiseError(
        "%s: failed with exit code %i\n" % (args[0], exitCode)
        )

  @memoise
  def _getCommonArgs(self):
    args = [
      '-msgstyle', 'parseable',  # Use parseable message output
      '-nowraplines',            # Don't wrap long lines
      '-sdatathreshold', '0',    # Max size for objects in small data section
      '-sdata2threshold', '0',   # Ditto for const small data section
      ]
    
    if self.warningsAsErrors:
      args.extend(['-w', 'error'])

    if self.debugSymbols:
      args.extend(['-sym', 'dwarf-2'])

    if self.__architecture == 'gekko':
      args.extend([
        '-processor', 'gekko',   # Target the Gekko processor
        '-fp', 'fmadd',          # Use fmadd instructions where possible
        ])
    
    return args
  
  @memoise
  def _getCompileArgs(self, language):
    args = [
      self.__ccExe,
      '-c',                      # Compile only
      '-MD',                     # Generate dependency file
      '-gccdep',                 # Output dependency file next to target 
      '-gccinc',                 # Use GCC #include semantics
      '-pragma', 'cats off',     # Turn off Codewarrior Analysis Tool
      '-enum', 'int',            # Enumerations always use 'int' for storage
      ]
    args.extend(self._getCommonArgs())

    args.extend(['-lang', language])

    if language == 'c++':
      if self.enableRtti:
        args.extend(['-RTTI', 'on'])
      else:
        args.extend(['-RTTI', 'off'])

    # Note: Exceptions are allowed for 'c' language
    if self.enableExceptions:
      args.extend(['-cpp_exceptions', 'on'])
    else:
      args.extend(['-cpp_exceptions', 'off'])

    if self.optimisation == self.NO_OPTIMISATION:
      args.extend([
        '-inline', 'off',
        '-opt', 'off',
        '-ipa', 'off',
        ])
    else:
      args.extend([
        '-inline', 'all',        # Let the compiler auto inline small functions
        '-opt', 'level=4',       # Optimize level 4
        '-opt', 'peep',          # Eliminate unnecessary moves/loads/stores
        '-opt', 'schedule',      # Reorder instructions to eliminate stalls
        '-str', 'reuse,pool',    # Reuse string constants, place them together
        ])

      if self.optimisation == self.PARTIAL_OPTIMISATION:
        args.extend(['-ipa', 'file'])
      elif self.optimisation == self.FULL_OPTIMISATION:
        args.extend(['-ipa', 'file'])
        # Note: ipa program requires you to:
        #  - link with cc.exe
        #  - pass '-ipa program' to the link
        #  - pass .irobj's to the link instead of .o's
        # Even after this the compiler may run out of memory trying
        # to optimise a large program. 
        #args.extend(['-ipa', 'program'])
  
    for p in reversed(self.includePaths):
      args.extend(['-i', p])

    args.extend('-D' + d for d in reversed(self.defines))
    
    for p in reversed(self.forceIncludes):
      args.extend(['-include', p])
    
    return args

  def getObjectCommands(self, target, source, engine):
    language = self.language
    if not language:
      if source.lower().endswith('.c'):
        language = 'c99'
      else:
        language = 'c++'
   
    args = list(self._getCompileArgs(language))
    args += [source, '-o', target]
    
    @makeCommand(args)
    def preprocess():
      self._executeProcess(args, target, engine)

    @makeCommand("obj-scan")
    def scan():
      dependencyFile = cake.path.stripExtension(target) + '.d'
      engine.logger.outputDebug(
        "scan",
        "scan: %s\n" % dependencyFile,
        )
      
      # TODO: Add dependencies on DLLs used by gcc.exe
      dependencies = [args[0]]
      dependencies.extend(parseDependencyFile(
        dependencyFile,
        self.objectSuffix
        ))
      return dependencies

    @makeCommand("dummy-compile")
    def compile():
      pass
      
    canBeCached = True
    return preprocess, scan, compile, canBeCached    

  @memoise
  def _getCommonLibraryArgs(self):
    args = [self.__ldExe, '-library']
    args.extend(self._getCommonArgs())
    return args
  
  def getLibraryCommand(self, target, sources, engine):
    args = list(self._getCommonLibraryArgs())
    args.extend(['-o', target])
    args.extend(sources)
    
    @makeCommand(args)
    def archive():
      cake.filesys.remove(target)
      self._executeProcess(args, target, engine)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by ld.exe
      return [args[0]] + sources

    return archive, scan

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = [self.__ldExe, '-application']
    args.extend(self._getCommonArgs())
    
    if self.linkerScript is not None:
      args.extend(['-lcf', self.linkerScript])

    return args
  
  def getProgramCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=False)
  
  def getModuleCommands(self, target, sources, engine):
    return self._getLinkCommands(target, sources, engine, dll=True)

  def _getLinkCommands(self, target, sources, engine, dll):
    resolvedPaths, unresolvedLibs = self._resolveLibraries(engine)
    
    args = list(self._getCommonLinkArgs(dll))
    args.extend(sources)
    args.extend(resolvedPaths)    
    args.extend('-L' + p for p in reversed(self.libraryPaths))
    args.extend('-l' + l for l in unresolvedLibs)    
    args.extend(['-o', target])

    if self.outputMapFile:
      args.extend(['-map', cake.path.stripExtension(target) + '.map'])
      
    @makeCommand(args)
    def link():
      self._executeProcess(args, target, engine)      
    
    @makeCommand("link-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by gcc.exe
      # Also add dependencies on system libraries, perhaps
      #  by parsing the output of ',Wl,--trace'
      return [args[0]] + sources + resolvedPaths
    
    return link, scan
