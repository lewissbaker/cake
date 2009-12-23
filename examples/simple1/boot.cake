import os.path
import cake.builders

import cake.tools.compilers.dummy as dummy

cake.builders.compiler = dummy.DummyCompiler()

import cake.bytecode as bytecode

cache = bytecode.CodeCache()

scriptPath = os.path.join(os.path.dirname(__file__), "source.cake")
code = cache.load(scriptPath)

exec code

#from cake.engine import Engine
#from cake.builder import Builder
#
#class Printer(Builder):
#  
#  INFO = 0
#  WARNING = 1
#  ERROR = 2
#  
#  def __init__(self, engine):
#    self._engine = engine
#    self.debugLevel = INFO
#    
#  def info(self, text):
#    if self.debugLevel <= INFO:
#      print text
#    
#  def warning(self, text):
#    if self.debugLevel <= WARNING:
#      print "WARN: " + text
#
#  def error(self, text):
#    if self.debugLevel <= ERROR:
#      print "ERROR: " + text
#
#engine = Engine()
#engine.register(Printer, type="printer")
#
#execution = engine.execute("source.cake", **keywords)

