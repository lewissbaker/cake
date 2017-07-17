"""The Clang Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.library import memoise
from cake.target import getPaths
from cake.library.compilers import Compiler, makeCommand, CompilerNotFoundError

import cake.path
import cake.filesys

import os.path

class ClangCompiler(Compiler):

  _name = 'clang'

  def __init__(self,
               configuration,
               clangExe,
               llvmArExe,
               binPaths):
    Compiler.__init__(self, configuration=configuration, binPaths=binPaths)
    self._clangExe = clangExe
    self._llvmArExe = llvmArExe

  def _getLanguage(self, suffix, pch=False):
    language = self.language
    if language is None:
      if suffix in self.cSuffixes:
        language = 'c'
      elif suffix in self.cppSuffixes:
        language = 'c++'

    return language

  @memoise
  def _getCommonCompileArgs(self, suffix, shared=False, pch=False):
    args = [self._clangExe, '-c', '-MD']

    language = self._getLanguage(suffix)
    if language:
      args.extend(['-x', language])

    if self.debugSymbols:
      args.append('-g')

    if language == 'c++':
      args.extend(self.cppFlags)
    elif language == 'c':
      args.extend(self.cFlags)

    for d in self.getDefines():
      args.extend(['-D', d])

    for p in getPaths(self.getIncludePaths()):
      args.extend(['-I', p])

    for p in getPaths(self.getForcedIncludes()):
      args.extend(['-include', p])

    return args

  def getObjectCommands(self, target, source, pch, shared):
    depPath = self._generateDependencyFile(target)
    args = list(self._getCommonCompileArgs(cake.path.extension(source), shared))
    args.extend([source, '-o', target])

    # TODO: Add support for pch

    def compile():
      dependencies = self._runProcess(args + ['-MF', depPath], target)
      dependencies.extend(self._scanDependencyFile(depPath, target))

      return dependencies

    canBeCached = True
    return compile, args, canBeCached

  @memoise
  def _getCommonLibraryArgs(self):
    args = [self._llvmArExe, 'qcs']
    args.extend(self.libraryFlags)
    return args

  def getLibraryCommand(self, target, sources):
    args = list(self._getCommonLibraryArgs())
    args.append(target)
    args.extend(getPaths(sources))

    @makeCommand("lib-scan")
    def scan():
      return [target], [args[0]] + sources

    @makeCommand(args)
    def archive():
      cake.filesys.remove(self.configuration.abspath(target))
      self._runProcess(args, target)

    return archive, scan

  def getProgramCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=False)

  def getModuleCommands(self, target, sources, importLibrary, installName):
    return self._getLinkCommands(target,
                                 sources,
                                 importLibrary,
                                 installName,
                                 dll=True)

  @memoise
  def _getCommonLinkArgs(self, dll):
    args = [self._clangExe]
    if dll:
      args.append('--shared')
      args.extend(self.moduleFlags)
    else:
      args.extend(self.programFlags)

    return args

  def _getLinkCommands(self, target, sources, importLibrary=None, installName=None, dll=False):

    objects, libraries = self._resolveObjects()

    args = list(self._getCommonLinkArgs(dll))

    for path in getPaths(self.getLibraryPaths()):
      args.append('-L' + path)
    
    args.extend(['-o', target])
    
    args.extend(sources)
    
    args.extend(objects)

    for lib in libraries:
      if cake.path.baseName(lib) == lib:
        args.append('-l' + lib)
      else:
        args.append(lib)

      
    @makeCommand(args)
    def link():
      self._runProcess(args, target)

    @makeCommand("link-scan")
    def scan():
      targets = [target]
      if dll and importLibrary:
        targets.append(importLibrary)
      dependencies = [args[0]]
      dependencies += sources
      dependencies += objects
      dependencies += self._scanForLibraries(libraries)
      return targets, dependencies

    return link, scan
  
