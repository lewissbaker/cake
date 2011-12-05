#-------------------------------------------------------------------------------
# This example demonstrates creating a project and solution using the project
# tool.
#
# Note that the example must be run with '-p' or '--projects' on the command
# line to generate the projects.
#-------------------------------------------------------------------------------
from cake.tools import script, project

# Build the main program.
script.execute("main/build.cake")
  
# Build the solution. Use the 'project' result of the main programs build.cake
# as one of the solutions project files.
project.solution(
  target="../build/project/createproject/createproject",
  projects=[script.getResult("main/build.cake", "project")],
  )
