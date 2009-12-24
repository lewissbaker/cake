import cake.task as task
import sys

def printHello():
  sys.stdout.write("Hello")
  
def printWorld():
  sys.stdout.write(" world")
  
helloTask = task.Task(printHello)
worldTask = task.Task(printWorld)
worldTask.dependsOn(helloTask)

worldTask.run() # Should wait on hello task
helloTask.run() # Should run hello task followed by world task
