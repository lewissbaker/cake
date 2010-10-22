#-------------------------------------------------------------------------------
# Script used to run a python function.
#-------------------------------------------------------------------------------
import cake.filesys
import cake.path
from cake.tools import script, logging

path = "path/to/tool.exe"

class TestTool(object):
  
  def build(self, target):
    # Create a function that will output a dummy target file
    def run():
      logging.outputInfo("[TestTool] %s: (%s)\n" % (path, target))
      absTarget = script.configuration.abspath(target)
      cake.filesys.makeDirs(cake.path.dirName(absTarget))
      open(absTarget, 'wb').close() 

    # Use the script tool to run our function. Note that we could also
    # add source file dependencies by passing a 'sources' argument.
    return script.run(run, targets=[target], args=[path, self.name])[0]
  
tool = TestTool()
target = tool.build(script.cwd("../build/pythontool/target"))
target.task.addCallback(lambda: logging.outputInfo("pythontool finished\n"))
