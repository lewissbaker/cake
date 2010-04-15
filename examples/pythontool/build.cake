import cake.filesys
import cake.path
from cake.tools import script, env, logging

path = "path/to/tool.exe"

class TestTool(object):
  
  def __init__(self, name):
    self.name = name
    
  def build(self, target):
    engine = script.engine
    configuration = script.configuration

    def run():
      absTarget = configuration.abspath(target)
      logging.outputInfo("[%s] %s: (%s)\n" % (self.name, path, target))
      cake.filesys.makeDirs(cake.path.dirName(absTarget))
      open(absTarget, 'wb').close() 

    return script.run(run, targets=[target], args=[path, self.name])[0]
  
tool = TestTool(name="tool")
target = tool.build(env.expand('${BUILD}/pythontool/target'))
target.task.addCallback(lambda: logging.outputInfo("pythontool finished\n"))
