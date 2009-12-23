'''
Created on 22/12/2009

@author: Bugs Bunny
'''

from cake.tools.compilers import Compiler, CompilerResult

class DummyCompiler(Compiler):
  
  def __init__(self):

    Compiler.__init__(self)

  def object(self, target, source):
    
    print "Compiling object %s to %s" % (source, target)
    return CompilerResult([target], None)
    
  def objects(self, target, sources):
    
    print "Compiling objects %s to %s" % (str(sources), target)
    return CompilerResult([target], None)
    
  def library(self, target, sources):
    
    print "Compiling objects %s to %s" % (str(sources), target)
    return CompilerResult([target], None)
    
  def module(self, target, sources):
    
    print "Compiling objects %s to %s" % (str(sources), target)
    return CompilerResult([target], None)
    
  def executable(self, target, sources):
    
    print "Compiling objects %s to %s" % (str(sources), target)
    return CompilerResult([target], None)
      