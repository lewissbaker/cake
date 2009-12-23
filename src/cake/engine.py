
class VariantFactory(object):
  
  def __init__(self, factory, **keywords):
    self._factory = factory
    self._keywords = keywords

class Engine(object):
  """Main object that holds all of the singleton resources for a build.
  """
  
  def __init__(self):
    self._registry = {}
  
  def register(self, factory, **keywords):
    """Register a build variant.
    
    Replaces an existing variant with the same keywords.
    
    @param factory: A callable called with a single arg which is this
    builder object. Should return 
    @param kwargs: A set of key/value pairs identifying this build
    variant.
    """
    self._registry[keywords] = VariantFactory(factory, keywords)
  
  def include(self, path, builders):
    script = Script(self, path, builders)
    script.execute()
    