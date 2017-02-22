"""Defines common target classes.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import types

from cake.task import Task
from cake.async import AsyncResult

class Target(object):
  """Base class for targets that are built asynchronously.

  @ivar task: A task that completes when the target has been built.
  @type task: L{Task}
  """

  __slots__ = ["task"]

  def __init__(self, task=None):
    self.task = task

class FileTarget(Target):
  """A class returned by tools that produce a file result.
  
  @ivar path: The path to the target file.
  @type path: string
  @ivar task: A task that completes when the target file has been built. 
  @type task: L{Task}
  """

  __slots__ = ["path"]

  def __init__(self, path, task=None):
    super(FileTarget, self).__init__(task)
    self.path = path

  def __str__(self):
    return self.path

  def __repr__(self):
    return "<FileTarget(%r)>" % self.path

class DirectoryTarget(Target):
  """A class returned by tools that produce a directory result.
  
  @ivar path: The path to the target directory.
  @type path: string
  @ivar task: A task that completes when the target directory has been written. 
  @type task: L{Task}
  """
  
  __slots__ = ["path"]

  def __init__(self, path, task=None):
    super(DirectoryTarget, self).__init__(task)
    self.path = path

  def __str__(self):
    """Return the string representation of this object.
    """
    return self.path

  def __repr__(self):
    return "<DirectoryTarget(%r)>" % self.path

_sequenceTypes = (list, tuple, set, frozenset, types.GeneratorType)

def getTasks(values):
  """Get a list of tasks from the specified value.

  @param values: A sequence of values, potentially containing
  Task or Target values that you want to wait on.

  @return: A list containing all Tasks found in C{value}.
  @rtype: C{list} of L{Task}
  """
  assert not isinstance(values, AsyncResult)

  tasks = []
  for value in values:
    task = getTask(value)
    if task is not None:
      tasks.append(task)
  return tasks

def getTask(value):
  """Get the task that builds this target or file.
  
  @param value: The Target, Task, string or list of these.
  
  @return: Returns a Task that will complete once all of the Task and
  Target tasks have completed.
  @rtype: L{Task} or C{None}
  """
  assert not isinstance(value, AsyncResult)

  if isinstance(value, Task):
    return value
  elif isinstance(value, Target):
    return value.task
  elif isinstance(value, _sequenceTypes):
    tasks = getTasks(value)
    if len(tasks) == 1:
      return tasks[0]
    elif tasks:
      task = Task()
      task.lazyStartAfter(tasks)
      return task
    else:
      return None
  else:
    return None

def getPath(file):
  """Get the path of a source file.

  Use this to extract the path of a file/directory when the file
  could be specified either as a FileTarget, DirectoryTarget or string.

  @param file: The object representing the file.
  @type file: L{FileTarget}, L{DirectoryTarget} or C{basestring}
  """
  assert not isinstance(file, AsyncResult)
    
  if isinstance(file, (FileTarget, DirectoryTarget)):
    return file.path
  elif isinstance(file, basestring):
    return file
  else:
    return None
  
def getPaths(files):
  """Get the paths in a list of sources or dependencies.
  
  @param files: A list of source objects to extract the paths from.
  @type files: C{list} of objects

  @return: A list of strings containing paths of any FileTarget, DirectoryTarget
  objects, or any strings in input (assumed to be paths).
  @rtype: C{list} of string
  """
  assert not isinstance(files, AsyncResult)
  assert not isinstance(files, basestring)

  paths = []
  for f in files:
    path = getPath(f)
    if path is not None:
      paths.append(path)
  return paths
