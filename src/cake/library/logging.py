"""Logging Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

from cake.engine import Script
from cake.library import Tool

class LoggingTool(Tool):
  
  def debugEnabled(self, keyword):
    """Returns True if currently debugging the given component.
    
    @param keyword: The component to check.
    @type keyword: string
    
    @return: True if the logger is debugging the given component,
    otherwise False.
    @rtype: bool
    """
    logger = Script.getCurrent().engine.logger
    return logger.debugEnabled(keyword)
    
  def outputError(self, message):
    """Output an error message.
    
    @param message: The message to output.
    @type message: string
    """
    logger = Script.getCurrent().engine.logger
    return logger.outputError(message)
      
  def outputWarning(self, message):
    """Output a warning message.
    
    @param message: The message to output.
    @type message: string
    """
    logger = Script.getCurrent().engine.logger
    return logger.outputWarning(message)
      
  def outputInfo(self, message):
    """Output an informative message.
    
    @param message: The message to output.
    @type message: string
    """
    logger = Script.getCurrent().engine.logger
    return logger.outputInfo(message)
      
  def outputDebug(self, keyword, message):
    """Output a debug message.
    
    The message will output only if the keyword matches a component
    we are currently debugging.
    
    @param keyword: The debug keyword associated with this message.
    @type keyword: string
    @param message: The message to output.
    @type message: string
    """
    logger = Script.getCurrent().engine.logger
    return logger.outputDebug(message)
    