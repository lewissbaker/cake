
class Builder(object):
  
  def __init__(self, engine, **keywords):
    self.engine = engine
    self.keywords = keywords
  
  def include(self, path):
    self.engine.include(path, [self])
