"""The Metrowerks CodeWarrior Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import os
import os.path

import cake.filesys
import cake.path
from cake.library import memoise, getPaths
from cake.library.compilers import Compiler, makeCommand
from cake.gnu import parseDependencyFile

class MwcwCompiler(Compiler):

  libraryPrefixSuffixes = [('', '.a')]
  programSuffix = '.elf'
  pchSuffix = '.mch'
  _name = 'mwcw'

  def __init__(
    self,
    configuration,
    ccExe=None,
    ldExe=None,
    binPaths=None,
    ):
    Compiler.__init__(self, configuration=configuration, binPaths=binPaths)
    self.__ccExe = ccExe
    self.__ldExe = ldExe

  def _formatMessage(self, inputText):
    """Format errors to be clickable in MS Visual Studio.
    """
    if self.messageStyle != self.MSVS_CLICKABLE:
      return inputText
    
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
  
  def _outputStdout(self, text):
    Compiler._outputStdout(self, self._formatMessage(text))

  def _outputStderr(self, text):
    Compiler._outputStderr(self, self._formatMessage(text))
    
  @memoise
  def _getCommonArgs(self):
    args = [
      '-msgstyle', 'parseable',  # Use parseable message output
      '-nowraplines',            # Don't wrap long lines
      ]
    
    if self.warningsAsErrors:
      args.extend(['-w', 'error'])

    if self.debugSymbols:
      args.extend(['-sym', 'dwarf-2'])
    
    return args
  
  @memoise
  def _getCompileArgs(self, suffix):
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

    if self.language is not None:
      args.extend(['-lang', self.language])

    language = self._getLanguage(suffix)
    if language in ['c++', 'cplus', 'ec++']:
      args.extend(self.cppFlags)
    elif language in ['c', 'c99']:
      args.extend(self.cFlags)
    elif language == 'objc':
      args.extend(self.mFlags)

    if self.enableRtti is not None:
      if self.enableRtti:
        args.extend(['-RTTI', 'on'])
      else:
        args.extend(['-RTTI', 'off'])
    
    if self.enableExceptions is not None:
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
    elif (
      self.optimisation == self.PARTIAL_OPTIMISATION or
      self.optimisation == self.FULL_OPTIMISATION
      ):
      args.extend([
        '-inline', 'all',        # Let the compiler auto inline small functions
        '-str', 'reuse,pool',    # Reuse string constants, place them together
        '-ipa', 'file',          # File level optimisation
        ])

      if self.optimisation == self.PARTIAL_OPTIMISATION:
        args.extend(['-opt', 'level=2']) # Optimisation level 2
      elif self.optimisation == self.FULL_OPTIMISATION:
        args.extend([
          '-opt', 'level=4',       # Optimisation level 4
          '-opt', 'peep',          # Eliminate unnecessary moves/loads/stores
          '-opt', 'schedule',      # Reorder instructions to eliminate stalls
          ])
        # Note: ipa program requires you to:
        #  - link with cc.exe
        #  - pass '-ipa program' to the link line
        #  - pass .irobj's to the link line instead of .o's
        # Even after this the compiler may run out of memory trying
        # to optimise a large program. 
        #args.extend(['-ipa', 'program']) # Whole program optimisation
  
    for p in self.getIncludePaths():
      args.extend(['-i', p])

    args.extend('-D' + d for d in self.getDefines())
    
    for p in getPaths(self.getForcedIncludes()):
      args.extend(['-include', p])
    
    return args
  
  def _getLanguage(self, suffix):
    language = self.language
    if language is None:
      if suffix in self.cSuffixes:
        language = 'c99'
      elif suffix in self.cppSuffixes:
        language = 'c++'
      elif suffix in self.mSuffixes:
        language = 'objc'
    return language

  def getPchCommands(self, target, source, header, object):
    depPath = self._generateDependencyFile(target)
    args = list(self._getCompileArgs(cake.path.extension(source)))
    args.extend([source, '-precompile', target])
    
    def compile():
      dependencies = self._runProcess(args + ['-MF', depPath], target)
      dependencies.extend(self._scanDependencyFile(depPath, target))
      return dependencies

    canBeCached = True
    return compile, args, canBeCached   
  
  def getObjectCommands(self, target, source, pch, shared):
    depPath = self._generateDependencyFile(target)
    args = list(self._getCompileArgs(cake.path.extension(source)))
    args.extend([source, '-o', target])
    
    if pch is not None:
      args.extend(['-include', pch.path])

    def compile():
      dependencies = self._runProcess(args + ['-MF', depPath], target)
      dependencies.extend(self._scanDependencyFile(depPath, target))
      
      if pch is not None:
        dependencies.append(pch.path)

      return dependencies

    canBeCached = True
    return compile, args, canBeCached    

  @memoise
  def _getCommonLibraryArgs(self):
    args = [self.__ldExe, '-library']
    args.extend(self._getCommonArgs())
    args.extend(self.libraryFlags)
    return args
  
  def getLibraryCommand(self, target, sources):
    args = list(self._getCommonLibraryArgs())
    args.extend(['-o', target])
    args.extend(sources)
    
    @makeCommand(args)
    def archive():
      cake.filesys.remove(self.configuration.abspath(target))
      self._runProcess(args, target)

    @makeCommand("lib-scan")
    def scan():
      # TODO: Add dependencies on DLLs used by ld.exe
      targets = [target]
      dependencies = [args[0]]
      dependencies += sources
      return targets, dependencies

    return archive, scan

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = [self.__ldExe, '-application']
    args.extend(self._getCommonArgs())
    
    if dll:
      args.extend(self.moduleFlags)
    else:
      args.extend(self.programFlags)
    
    if self.linkerScript is not None:
      args.extend(['-lcf', self.linkerScript])

    args.extend('-L' + p for p in self.getLibraryPaths())
    return args
  
  def getProgramCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=False)
  
  def getModuleCommands(self, target, sources, importLibrary, installName):
    return self._getLinkCommands(target, sources, importLibrary, installName, dll=True)

  def _getLinkCommands(self, target, sources, importLibrary=None, installName=None, dll=False):
    
    objects, libraries = self._resolveObjects()
    
    args = list(self._getCommonLinkArgs(dll))
    args.extend(sources)
    args.extend(objects)
    args.extend('-l' + l for l in libraries)    
    args.extend(['-o', target])

    if self.outputMapFile:
      mapFile = cake.path.stripExtension(target) + '.map'
      args.extend(['-map', mapFile])
      
    @makeCommand(args)
    def link():
      self._runProcess(args, target)      
    
    @makeCommand("link-scan")
    def scan():
      targets = [target]
      if self.outputMapFile:
        targets.append(mapFile)
        
      # TODO: Add dependencies on DLLs used by gcc.exe
      # Also add dependencies on system libraries, perhaps
      #  by parsing the output of ',Wl,--trace'
      dependencies = [args[0]]
      dependencies += sources
      dependencies += objects
      dependencies += self._scanForLibraries(libraries)
      
      return targets, dependencies
    
    return link, scan

class WiiMwcwCompiler(MwcwCompiler):

  @memoise
  def _getCommonArgs(self):
    args = MwcwCompiler._getCommonArgs(self)
    args.extend([
      '-processor', 'gekko',   # Target the Gekko processor
      '-fp', 'fmadd',          # Use fmadd instructions where possible
      '-sdatathreshold', '0',  # Max size for objects in small data section
      '-sdata2threshold', '0', # Ditto for const small data section
      ])
    return args
