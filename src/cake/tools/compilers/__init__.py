from cake.engine import Tool 

class CompilerResult(object):
  
  def __init__(self, targets, task):
    
    self.targets = targets
    self.task = task
  
class Compiler(Tool):
  
  NO_OPTIMISATION = 0
  SOME_OPTIMISATION = 1
  GLOBAL_OPTIMISATION = 2
  
  def __init__(self):
    
    self.debugSymbols = False
    self.optimisation = self.NO_OPTIMISATION
    self.includePaths = []
    self.defines = []
    
  def addIncludePath(self, path):
    
    self.includePaths.append(path)
    
  def addDefine(self, define):
    
    self.defines.append(define)
    
  def object(self, target, source):
    
    raise NotImplementedError()
    
  def objects(self, target, sources):
    
    raise NotImplementedError()
    
  def library(self, target, sources):
    
    raise NotImplementedError()
    
  def module(self, target, sources):
    
    raise NotImplementedError()
    
  def executable(self, target, sources):
    
    raise NotImplementedError()
        