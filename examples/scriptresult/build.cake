from cake.tools import script

library = script.getResult(script.cwd('other.cake'), 'library')
module = script.getResult(script.cwd('other.cake'), 'module')

def onLibraryDone():
  print "library path =", library.result
  
def onModuleDone():
  print "module path =", module.result
   
library.task.addCallback(onLibraryDone)
module.task.addCallback(onModuleDone)
