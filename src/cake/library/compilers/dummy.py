"""A Dummy Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import cake.filesys
import cake.path
from cake.library import memoise
from cake.target import getPaths
from cake.library.compilers import Compiler, makeCommand

class DummyCompiler(Compiler):
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib')]
  modulePrefixSuffixes = [('', '.dll')]
  programSuffix = '.exe'
  pchSuffix = '.pch'
  _name = 'dummy'
  
  def __init__(self, configuration):
    Compiler.__init__(self, configuration)

  @memoise
  def _getCompileArgs(self):
    args = ['cc', '/c']
    if self.debugSymbols:
      args.append('/debug')
    if self.optimisation != self.NO_OPTIMISATION:
      args.append('/O')
    if self.enableRtti:
      args.append('/rtti')
    if self.enableExceptions:
      args.append('/ex')
    if self.language:
      args.append('/lang:%s' % self.language)
    args.extend('/I%s' % p for p in self.getIncludePaths())
    args.extend('/D%s' % d for d in self.getDefines())
    args.extend('/FI%s' % p for p in getPaths(self.getForcedIncludes()))
    return args
  
  def getPchCommands(self, target, source, header, object):
    compilerArgs = list(self._getCompileArgs())
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
    compilerArgs = list(self._getCompileArgs())
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
      return [target], sources
      
    return archive, scan
 
  def getProgramCommands(self, target, sources):
    return self._getLinkCommands(target, sources, dll=False)
  
  def getModuleCommands(self, target, sources, importLibrary, installName):
    return self._getLinkCommands(target, sources, importLibrary, installName, dll=True)

  def _getLinkCommands(self, target, sources, importLibrary=None, installName=None, dll=False):
    objects, libraries = self._resolveObjects()

    libFlags = ['-l' + lib for lib in libraries]
    args = ['ld'] + sources + objects + libFlags + ['/o' + target]

    if importLibrary:
      importLibrary = self.configuration.abspath(importLibrary)
    
    @makeCommand(args)
    def link():
      self.engine.logger.outputDebug("run", "%s\n" % " ".join(args))
      absTarget = self.configuration.abspath(target)
      cake.filesys.writeFile(absTarget, "".encode("latin1"))
      if dll and importLibrary:
        cake.filesys.writeFile(importLibrary, "".encode("latin1"))
    
    @makeCommand("dummy-scanner")
    def scan():
      targets = [target]
      if dll and importLibrary:
        targets.append(importLibrary)
      dependencies = list(sources)
      dependencies += objects
      dependencies += self._scanForLibraries(libraries)
      return targets, dependencies
    
    return link, scan
