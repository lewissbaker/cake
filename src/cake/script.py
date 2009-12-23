'''
Created on 18/12/2009

@author: Bugs Bunny
'''

class Script(object):
  
  def __init__(self, engine, path, parent, overrides):
    self.engine = engine
    self.path = path
    self.builders = {}
    
  def include(self, path):
    pass
  
  def build(self, path):
    pass
  
  def builder(self, **keywords):
    pass

