"""A Dummy Compiler.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

__all__ = ["DummyCompiler"]

import cake.filesys
import cake.path
from cake.library import memoise
from cake.library.compilers import Compiler, makeCommand

class DummyCompiler(Compiler):
  
  objectSuffix = '.obj'
  libraryPrefixSuffixes = [('', '.lib')]
  moduleSuffix = '.dll'
  programSuffix = '.exe'
  
  def __init__(self):
    Compiler.__init__(self)

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
    args.extend('/I%s' % p for p in reversed(self.includePaths))
    args.extend('/D%s' % d for d in self.defines)
    args.extend('/FI%s' % p for p in self.forcedIncludes)
    return args

  def getObjectCommands(self, target, source, engine):

    language = self.language
    if not language:
      if source.lower().endswith('.c'):
        language = 'c'
      else:
        language = 'c++'

    compilerArgs = list(self._getCompileArgs(language))
    compilerArgs += [source, '/o' + target]
    
    def compile():
      engine.logger.outputDebug("run", "%s\n" % " ".join(compilerArgs))
      cake.filesys.makeDirs(cake.path.dirName(target))
      f = open(target, 'wb')
      f.close()
        
      dependencies = [source]
      return dependencies

    def command():
      task = engine.createTask(compile)
      task.start(immediate=True)
      return task

    canBeCached = True
    return command, compilerArgs, canBeCached

  def getLibraryCommand(self, target, sources, engine):
    
    args = ['ar'] + sources + ['/o' + target]

    @makeCommand(args)
    def archive():
      engine.logger.outputDebug("run", "%s\n" % " ".join(args))
      cake.filesys.makeDirs(cake.path.dirName(target))
      f = open(target, 'wb')
      f.close()
      
    @makeCommand("dummy-scanner")
    def scan():
      return sources
      
    return archive, scan
  
  def getProgramCommands(self, target, sources, engine):
    args = ['ld'] + sources + ['/o' + target]
    
    @makeCommand(args)
    def link():
      engine.logger.outputDebug("run", "%s\n" % " ".join(args))
      cake.filesys.makeDirs(cake.path.dirName(target))
      f = open(target, 'wb')
      f.close()
    
    @makeCommand("dummy-scanner")
    def scan():
      return sources
    
    return link, scan
    
  def getModuleCommands(self, target, sources, engine):
    # Lazy
    return self.getProgramCommands(target, sources, engine)