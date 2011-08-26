#-------------------------------------------------------------------------------
# This example demonstrates setting and obtaining the result of a script.
#-------------------------------------------------------------------------------
from cake.tools import script, logging

library = script.getResult('other.cake', 'library')
module = script.getResult('other.cake', 'module')

def onLibraryDone():
  logging.outputInfo("library path = %s\n" % library.result)
  
def onModuleDone():
  logging.outputInfo("module path = %s\n" % module.result)
   
library.task.addCallback(onLibraryDone)
module.task.addCallback(onModuleDone)
