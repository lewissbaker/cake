
class FileTarget(object):
  
  def __init__(self, path, task):
    self.path = path
    self.task = task

def getPathAndTask(file):
  if isinstance(file, FileTarget):
    return file.path, file.task
  else:
    return file, None

def getPathsAndTasks(files):
  paths = []
  tasks = []
  for f in files:
    if isinstance(f, FileTarget):
      paths.append(f.path)
      tasks.append(f.task)
    else:
      paths.append(f)
  return paths, tasks
