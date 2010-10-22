"""A Dummy Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

__all__ = ["DummyCompiler"]

import cake.filesys
import cake.path
from cake.library import memoise, getPaths
from cake.library.compilers import Compiler, makeCommand

class DummyCompiler(Compiler):
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib')]
  modulePrefixSuffixes = [('', '.dll')]
  programSuffix = '.exe'
  pchSuffix = '.pch'
  
  def __init__(self, configuration):
    Compiler.__init__(self, configuration)

  @memoise
  def _getCompileArgs(self, language):
    args = ['cc', '/c']
    if self.debugSymbols:
      args.append('/debug')
    if self.optimisation != self.NO_OPTIMISATION:
      args.append('/O')
    if self.enableRtti:
      args.append('/rtti')
    if self.enableExceptions:
      args.append('/ex')
    if language:
      args.append('/lang:%s' % language)
    args.extend('/I%s' % p for p in self.getIncludePaths())
    args.extend('/D%s' % d for d in self.getDefines())
    args.extend('/FI%s' % p for p in getPaths(self.getForcedIncludes()))
    return args

  def getPchCommands(self, target, source, header, object):
    language = self.language
    if not language:
      if source.lower().endswith('.c'):
        language = 'c'
      else:
        language = 'c++'

    compilerArgs = list(self._getCompileArgs(language))
    compilerArgs += ['/H' + header, source, '/o' + target]
    
    def compile():
      self.engine.logger.outputDebug("run", "%s\n" % " ".join(compilerArgs))
      absTarget = self.configuration.abspath(target)
      cake.filesys.writeFile(absTarget, "".encode("latin1"))
      dependencies = [source]
      return dependencies

    canBeCached = True
    return compile, compilerArgs, canBeCached

  def getObjectCommands(self, target, source, pch, shared):
    language = self.language
    if not language:
      if source.lower().endswith('.c'):
        language = 'c'
      else:
        language = 'c++'

    compilerArgs = list(self._getCompileArgs(language))
    compilerArgs += [source, '/o' + target]
    
    def compile():
      self.engine.logger.outputDebug("run", "%s\n" % " ".join(compilerArgs))
      absTarget = self.configuration.abspath(target)
      cake.filesys.writeFile(absTarget, "".encode("latin1"))
        
      dependencies = [source]
      if pch is not None:
        dependencies.append(pch.path)
      return dependencies

    canBeCached = True
    return compile, compilerArgs, canBeCached

  def getLibraryCommand(self, target, sources):
    args = ['ar'] + sources + ['/o' + target]

    @makeCommand(args)
    def archive():
      self.engine.logger.outputDebug("run", "%s\n" % " ".join(args))
      absTarget = self.configuration.abspath(target)
      cake.filesys.writeFile(absTarget, "".encode("latin1"))
      
    @makeCommand("dummy-scanner")
    def scan():
      return sources
      
    return archive, scan
 
  def getProgramCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=False)
  
  def getModuleCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=True)

  def _getLinkCommands(self, target, sources, dll):
    objects, libraries = self._resolveObjects()

    args = ['ld'] + sources + objects + ['/o' + target]
    
    @makeCommand(args)
    def link():
      self.engine.logger.outputDebug("run", "%s\n" % " ".join(args))
      absTarget = self.configuration.abspath(target)
      cake.filesys.writeFile(absTarget, "".encode("latin1"))
      if self.importLibrary:
        importLibrary = self.configuration.abspath(self.importLibrary)
        cake.filesys.writeFile(importLibrary, "".encode("latin1"))
    
    @makeCommand("dummy-scanner")
    def scan():
      dependencies = sources + objects + self._scanForLibraries(libraries)
      if self.importLibrary:
        importLibrary = self.configuration.abspath(self.importLibrary)
        dependencies.append(importLibrary)
      return dependencies    
    return link, scan
