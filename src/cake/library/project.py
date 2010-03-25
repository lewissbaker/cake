"""Project Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys
import threading
import os.path
import codecs
try:
  import cStringIO as StringIO
except ImportError:
  import StringIO

import cake.path
import cake.filesys
import cake.hash
from cake.engine import Script
from cake.library import Tool, FileTarget, getPathsAndTasks

class Project(object):
  
  def __init__(self, path):
    
    self.path = path
    self.dir = cake.path.dirName(path)
    self.name = cake.path.baseNameWithoutExtension(path)
    self.sccProvider = None
    self.sccProjectName = None
    self.sccAuxPath = None
    self.sccLocalPath = None
    self.internalGuid = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"
    self.externalGuid = generateGuid(path)
    self.configurations = {}
    self.lock = threading.Lock()
    
  def setName(self, name):
    
    self.name = name
    
  def addConfiguration(self, configuration):
    
    self.lock.acquire()
    try:
      if configuration.name in self.configurations:
        raise ValueError("Project '%s' already has configuration '%s'." % (
            self.path,
            configuration.name,
            ))
      self.configurations[configuration.name] = configuration
    finally:
      self.lock.release()  
      
class ProjectConfiguration(object):

  def __init__(
    self,
    name,
    items,
    buildArgs,
    outputs,
    intermediateDir,
    defines,
    includePaths,
    forcedIncludes,
    forcedUsings,
    ):
    
    self.name = name
    self.items = items
    self.buildArgs = buildArgs
    self.outputs = outputs
    self.intermediateDir = intermediateDir
    self.defines = defines
    self.includePaths = includePaths
    self.forcedIncludes = forcedIncludes
    self.forcedUsings = forcedUsings

class Solution(object):
  
  def __init__(self, path):
    
    self.path = path
    self.dir = cake.path.dirName(path)
    self.name = cake.path.baseNameWithoutExtension(path)
    self.configurations = {}
    self.lock = threading.Lock()
    
  def getConfiguration(self, name):
    
    self.lock.acquire()
    try:
      solutionConfig = self.configurations.get(name, None)
      if solutionConfig is None:
        solutionConfig = SolutionConfiguration(name)
        self.configurations[name] = solutionConfig
      return solutionConfig
    finally:
      self.lock.release()  
    
class SolutionConfiguration(object):
  
  def __init__(self, name):
    
    self.name = name
    self.projectConfigurations = []
    
  def addProjectConfiguration(self, configuration):

    self.projectConfigurations.append(configuration) 

class SolutionProjectConfiguration(object):
  
  def __init__(self, name, path):
    
    self.name = name
    self.path = path

class ProjectRegistry(object):
  
  def __init__(self):
    
    self.projects = {}
    self.lock = threading.Lock()
    
  def getProject(self, path):
    
    key = os.path.normpath(os.path.normcase(path))
    self.lock.acquire()
    try:
      project = self.projects.get(key, None)
      if project is None:
        project = Project(path)
        self.projects[key] = project
      return project
    finally:
      self.lock.release()  

  def getProjectByPath(self, path):
    
    key = os.path.normpath(os.path.normcase(path))
    return self.projects.get(key, None)
  
class SolutionRegistry(object):
  
  def __init__(self):
    
    self.solutions = {}
    self.lock = threading.Lock()
    
  def getSolution(self, path):
    
    key = os.path.normpath(os.path.normcase(path))
    self.lock.acquire()
    try:
      solution = self.solutions.get(key, None)
      if solution is None:
        solution = Solution(path)
        self.solutions[key] = solution
      return solution  
    finally:
      self.lock.release()  

class ProjectTool(Tool):
  
  enabled = True
  projectSuffix = '.vcproj'
  solutionSuffix = '.sln'
  _projects = ProjectRegistry()
  _solutions = SolutionRegistry()
  
  def __init__(self):
    super(ProjectTool, self).__init__()
    
  def project(
    self,
    target,
    configName,
    items,
    outputs,
    name=None,
    intermediateDir=None,
    ):
    """Generate a project file.
    
    @param target: The path for the generated project file. If this path
    doesn't have the correct suffix it will be appended automatically.
    @type target: string
    @param items: A list of strings or dict of string->(dict or list
    of string) specifying the paths to project folders and their files.
    Example::
      items={
        "Include":["vector.h", "integer.h"],
        "Source":{
          "PC":["vector_PC.cpp"],
          "Wii":["vector_Wii.cpp"],
          "":["integer.cpp"],
          },
        },
        
    Result::
      + Include
        - vector.h
        - integer.h
      + Source
        + PC
          - vector_PC.cpp
        + Wii
          - vector_Wii.cpp
        - integer.cpp
    
    @type items: list/dict of string
    @param outputs: A list of output files that this project generates.
    The first output file should be the executable used for debugging
    purposes (if applicable).
    @type outputs: list of string
    @param name: The name of the generated project. If this is None the
    base filename of the target is used instead.
    @type name: string
    @param intermediateDir: The path to intermediate files. If this is
    None the directory of the first output is used instead.
    @type intermediateDir: string

    @return: A L{FileTarget} that specifies the full path to the
    generated project file (with extension if applicable).
    @rtype: L{FileTarget}
    """
    target = cake.path.forceExtension(target, self.projectSuffix)
    
    if not self.enabled:
      return FileTarget(path=target, task=None)
    
    outputs, _ = getPathsAndTasks(outputs)

    # Project name defaults the base filename without extension
    if name is None:
      name = cake.path.baseNameWithoutExtension(target)
    
    # Intermediate dir defaults to the first outputs dir
    if intermediateDir is None:
      intermediateDir = cake.path.dirName(outputs[0])

    script = Script.getCurrent()

# TODO: Get these from target.defines, target.includePaths etc.. too
    defines = []
    includePaths = []
    forcedIncludes = []
    forcedUsings = []

    # Construct the build args
    cakeScript = sys.argv[0]
    targetDir = cake.path.dirName(target)
    keywords = script.variant.keywords

    buildArgs = [
      "python",
      "-u",
      cakeScript,
      cake.path.relativePath(script.path, targetDir),
      ]
    buildArgs.extend("=".join([k, v]) for k, v in keywords.iteritems())
    
    project = self._projects.getProject(target)
    project.setName(name)
    project.addConfiguration(ProjectConfiguration(
      configName,
      items,
      buildArgs,
      outputs,
      intermediateDir,
      defines,
      includePaths,
      forcedIncludes,
      forcedUsings,
      ))
    
    return FileTarget(path=target, task=None)
    
  def solution(self, configName, projectConfigName, target, projects):
    """Generate a solution file.
    
    @param target: The path for the generated solution file. If this path
    doesn't have the correct suffix it will be appended automatically.
    @type target: string
    @param projects: A list of projects to include in the solution. If
    any of the projects listed don't have the correct suffix it will be
    appended automatically.
    @type projects: list of string
    """
    target = cake.path.forceExtension(target, self.solutionSuffix)

    if not self.enabled:
      return FileTarget(path=target, task=None)

    projects = [
      cake.path.forceExtension(p, self.projectSuffix) for p in projects
      ]
    
    solution = self._solutions.getSolution(target)
    configuration = solution.getConfiguration(configName)
    
    for p in projects:
      configuration.addProjectConfiguration(SolutionProjectConfiguration(
        projectConfigName,
        p, 
        ))

    return FileTarget(path=target, task=None)
  
  def build(self, engine):
    """Build project and solution files.
    
    This function will actually write the project and solution files,
    provided the files on disk are different to the files being written.
    If the engine.forceBuild flag is set to True the files will be written
    regardless of any differences.
    
    @param engine: The cake.engine instance.
    @type engine: L{Engine}
    """    
    # Generate solutions first as they will attempt to reload in Visual
    # studio and automatically reload all changed projects too. This
    # saves having to click reload on every project change (most of
    # the time).
    for solution in self._solutions.solutions.values():
      generator = MsvsSolutionGenerator(solution, self._projects)
      generator.build(engine)

    for project in self._projects.projects.values():
      generator = MsvsProjectGenerator(project)
      generator.build(engine)

def escapeAttr(value):
  """Utility function for escaping xml attribute values.

  @param value: The string to XML attribute escape.

  @return: The escaped XML attribute string.
  """
  value = value.replace("&", "&amp;")
  value = value.replace("'", "&apos;")
  value = value.replace('"', "&quot;")
  return value

def generateGuid(filePath):
    """This generates a dummy GUID for the sln/vcproj file to use.
    It is based on the MD5 signatures of the sln filename plus the name of
    the project.  It basically just needs to be unique, and not
    change with each invocation.
    """
    sig = cake.hash.md5(os.path.normpath(os.path.normcase(filePath))).hexdigest().upper()
    # convert most of the signature to GUID form (discard the rest)
    guid = "{%s-%s-%s-%s-%s}" % (
      sig[:8], sig[8:12], sig[12:16], sig[16:20], sig[20:32],
      )
    return guid

def convertToProjectItems(srcfiles, projectDir):
  """Convert the dictionary-based datastructure for defining project items
  and filters into ProjectItem objects.

  @param srcfiles: A dictionary mapping filter names to either a list of
  files or to a similar dictionary. An empty sub-item name in the dictionary
  indicates that the sub-item list should be added to the parent's sub-items.
  eg. Passing this structure:
     {'Sources' :
       {'Private' : ['fooimpl.cpp', 'barimpl.cpp'],
        '' : ['foo.cpp'],
        },
       'Headers' : ['foo.h'],
       '' : ['source.cake'],
       }
  will return this hierarchy of items:
   + ProjectFilterItem('Sources')
   | + ProjectFilterItem('Private')
   | | + ProjectFileItem('fooimpl.cpp')
   | | + ProjectFileItem('barimpl.cpp')
   | + ProjectFileItem('foo.cpp')
   + ProjectFilterItem('Headers')
   | + ProjectFileItem('foo.h')
   + ProjectFileItem('source.cake')

  @param projectDir: The path of the directory containing the project file.
  All paths to file items are output relative to this directory.

  @return: A list of top-level ProjectItem objects to place in the project.
  """

  results = []
  if isinstance(srcfiles, dict):
    for name in srcfiles:
      subItems = convertToProjectItems(srcfiles[name], projectDir)
      if name:
        filterNode = ProjectFilterItem(name)
        filterNode.addSubItems(subItems)
        results.append(filterNode)
      else:
        results.extend(subItems)
  elif isinstance(srcfiles, list):
    for filePath in srcfiles:
      relPath = cake.path.relativePath(filePath, projectDir)
      fileItem = ProjectFileItem(relPath)
      results.append(fileItem)
  else:
    raise ValueError(
      "Expected dictionary or list for 'srcfiles' value."
      )
  return results

class ProjectItem(object):
  """I am an item in the project.
  """
  __slots__ = ['name']

  kind = 'unknown'

  def __init__(self, name):
    self.name = name

class ProjectFilterItem(ProjectItem):
  """I am a filter item in the project.

  Filters are like folders and can contain other sub-items.
  """

  __slots__ = ['subItems']

  kind = 'filter'

  def __init__(self, name):
    ProjectItem.__init__(self, name)
    self.subItems = []

  def addSubItems(self, subItems):
    """Add a sequence of sub-items to this filter.
    """
    self.subItems.extend(subItems)

class ProjectFileItem(ProjectItem):
  """I am a file item in the project.

  File items represent files in the project. They are typically leaf nodes
  in the solution explorer hierarchy.
  """

  __slots__ = ['filePath']

  kind = 'file'

  def __init__(self, filePath):
    """Construct a file-item in the project.
    
    @param filePath: Path of the file relative to the project file. 
    """
    ProjectItem.__init__(self, os.path.basename(filePath))
    self.filePath = filePath

_msvsProjectHeader = """\
<?xml version="1.0" encoding="%(encoding)s"?>
<VisualStudioProject
\tProjectType="Visual C++"
\tVersion="%(version)s"
\tName="%(name)s"
\tProjectGUID="%(guid)s"
%(scc_attrs)s
\tKeyword="MakeFileProj"
\t>
"""

_msvsProjectTailer = """\
</VisualStudioProject>
"""

_msvsProjectConfigurationHeader = """\
\t\t<Configuration
\t\t\tName="%(name)s"
\t\t\tOutputDirectory="%(outdir)s"
\t\t\tIntermediateDirectory="%(intdir)s"
\t\t\tConfigurationType="0"
\t\t\tUseOfMFC="0"
\t\t\tATLMinimizesCRunTimeLibraryUsage="FALSE"
\t\t\tBuildLogFile="%(buildlog)s"
\t\t\t>
"""

_msvsProjectConfigurationMakeTool = """\
\t\t\t<Tool
\t\t\t\tName="VCNMakeTool"
\t\t\t\tBuildCommandLine="%(buildcmd)s"
\t\t\t\tRebuildCommandLine="%(rebuildcmd)s"
\t\t\t\tCleanCommandLine="%(cleancmd)s"
\t\t\t\tOutput="%(runfile)s"
\t\t\t\tPreProcessorDefinitions="%(defines)s"
\t\t\t\tIncludeSearchPath="%(includes)s"
\t\t\t\tForcedIncludes="%(forcedinc)s"
\t\t\t/>
"""

_msvsProjectConfigurationXboxDeploymentTool = """\
\t\t\t<Tool
\t\t\t\tName="VCX360DeploymentTool"
\t\t\t\tRemoteRoot="devkit:\$(ProjectName)"
\t\t\t\tDeploymentType="0"
\t\t\t/>
"""

_msvsProjectConfigurationTailer = """\
\t\t</Configuration>
"""

class MsvsProjectGenerator(object):
  """I am a class that is able to generate a single .vcproj file from
  its configuration information.
  """

  # Default member values
  file = None
  encoding = 'utf-8'
  version = '8.00'

  def __init__(self, project):
    """Construct a new project generator instance.

    @param project: A Project object containing all info required for the project.

    @param sccProvider: The string identifying the MSVS SCC provider 
    """
    self.project = project
    self.projectName = project.name
    self.projectDir = project.dir
    self.projectFilePath = project.path
    self.configs = project.configurations.values()
    self.sccProvider = project.sccProvider
    
    if project.sccProjectName is None:
      self.sccProjectName = self.projectName
    else:
      self.sccProjectName = str(project.sccProjectName)
      
    if project.sccAuxPath is None:
      self.sccAuxPath = ""
    else:
      self.sccAuxPath = str(project.sccAuxPath)
      
    if project.sccLocalPath is None:
      self.sccLocalPath = "."
    else:
      self.sccLocalPath = str(project.sccLocalPath)

    # Get a unique set of platforms
    self.platforms = list(frozenset(
      c.name.split("|", 1)[1] for c in self.configs
      ))
    self.platforms.sort()

  def build(self, engine):
    """Create and write the .vcproj file.

    Throws an exception if building the project file fails.
    """
    stream = StringIO.StringIO()
    self.file = codecs.getwriter(self.encoding)(stream)
    try:
      self._writeProject()
    except:
      self.file.close()
      self.file = None
      raise
    newFileContents = stream.getvalue()
    self.file.close()
    self.file = None
    
    shouldBuild = engine.forceBuild
    if not shouldBuild:
      # Compare new file contents against existing file
      existingFileContents = None
      try:
        f = open(self.projectFilePath, "rb")
        try:
          existingFileContents = f.read()
          shouldBuild = newFileContents != existingFileContents
        finally:
          f.close()
      except EnvironmentError:
        shouldBuild = True
    
    if shouldBuild:
      engine.logger.outputInfo("Generating Project %s\n" % self.projectFilePath)
      cake.filesys.makeDirs(self.projectDir)
      open(self.projectFilePath, "wb").write(newFileContents)
    else:
      engine.logger.outputDebug(
        "project",
        "Skipping Identical Project %s\n" % self.projectFilePath,
        )
    
  def _writeProject(self):
    """Write the project to the currently open file.
    """
    self._writeProjectHeader()
    self._writePlatforms()
    self._writeConfigurations()
    self._writeFiles()
    self._writeProjectTailer()

  def _writeProjectHeader(self):
    """Write the project header section to the currently open file.

    This should be written at the start of the file.
    """

    guid = self.project.externalGuid

    if self.sccProvider:
      scc_attrs = ('\tSccProjectName="%(name)s"\n'
                   '\tSccProvider="%(provider)s"\n'
                   '\tSccAuxPath="%(auxpath)s"\n'
                   '\tSccLocalPath="%(localpath)s"' %
                   {'name' : escapeAttr(self.sccProjectName),
                    'provider' : escapeAttr(self.sccProvider),
                    'auxpath' : escapeAttr(self.sccAuxPath),
                    'localpath' : escapeAttr(self.sccLocalPath),
                    })
    else:
      scc_attrs = ""
    
    self.file.write(_msvsProjectHeader % {
      'encoding' : escapeAttr(self.encoding),
      'version' : escapeAttr(self.version),
      'name' : escapeAttr(self.projectName),
      'guid' : escapeAttr(guid),
      'scc_attrs' : scc_attrs,
      })

  def _writeProjectTailer(self):
    """Write the project tailer to the file.

    This should be the last content written to the file as it closes off
    datastructures written by the header.
    """
    self.file.write(_msvsProjectTailer)

  def _writePlatforms(self):
    """Write the section that declares all of the platforms supported by this
    project.
    """
    self.file.write("\t<Platforms>\n")
    for platform in self.platforms:
      self.file.write('\t\t<Platform\n')
      self.file.write('\t\t\tName="%s"\n' % escapeAttr(platform))
      self.file.write('\t\t/>\n')
    self.file.write("\t</Platforms>\n")

  def _writeConfigurations(self):
    """Write the section that declares all of the configurations supported by
    this project.
    """
    self.file.write("\t<Configurations>\n")
    for config in self.configs:
      self._writeConfiguration(config)
    self.file.write("\t</Configurations>\n")

  def _writeConfiguration(self, config):
    """Write a section that declares an individual build configuration.
    """
    relativePath = lambda p: cake.path.relativePath(p, self.projectDir)
    
    outdir = relativePath(os.path.dirname(config.outputs[0]))
    intdir = relativePath(config.intermediateDir)
    runfile = relativePath(config.outputs[0])
    buildlog = os.path.join(intdir, "buildlog.html")

    includePaths = ';'.join(config.includePaths)
    forcedIncludes = ';'.join(config.forcedIncludes)

    def formatDefine(define):
      if isinstance(define, tuple):
        return "%s=%s" % (str(define[0]), str(define[1]))
      else:
        return str(define)

    defines = [formatDefine(d) for d in config.defines]
    defines = ';'.join(defines)
      
    name = config.name

    def escapeArg(arg):
      if '"' in arg:
        arg = arg.replace('"', '\\"')
      if " " in arg:
        arg = '"' + arg + '"'
      return arg
    
    def escapeArgs(args):
      return [escapeArg(arg) for arg in args]

    args = escapeArgs(list(config.buildArgs))

    buildCmd = " ".join(args)
    cleanCmd = buildCmd + " -clean-not-implemented"
    rebuildCmd = buildCmd + " -f"

    self.file.write(_msvsProjectConfigurationHeader % {
      'name' : escapeAttr(name),
      'outdir' : escapeAttr(outdir),
      'intdir' : escapeAttr(intdir),
      'buildlog' : escapeAttr(buildlog),
      })
    
    self.file.write(_msvsProjectConfigurationMakeTool % {
      'buildcmd' : escapeAttr(buildCmd),
      'rebuildcmd' : escapeAttr(rebuildCmd),
      'cleancmd' : escapeAttr(cleanCmd),
      'runfile' : escapeAttr(runfile),
      'defines' : escapeAttr(defines),
      'includes' : escapeAttr(includePaths),
      'forcedinc' : escapeAttr(forcedIncludes),
      })
    
    if config.name.endswith("|Xbox 360"):
      self.file.write(_msvsProjectConfigurationXboxDeploymentTool)

    self.file.write(_msvsProjectConfigurationTailer)
            
  def _writeFiles(self):

    configItems = {}
    for config in self.configs:
      configItems[config] = convertToProjectItems(config.items, self.projectDir)
    
    self.file.write("\t<Files>\n")
    self._writeSubItems(configItems, indent='\t\t')
    self.file.write("\t</Files>\n")

  def _writeSubItems(self, configItems, indent):
    """Recursively write out all of the subitems.

    configItems - A dictionary mapping from the ConfigurationNode
    to a list of the items to write for that configuration.
    """

    mergedFileItemConfigs = {}
    mergedFilterSubItems = {}

    # Merge the subitems from each config
    for config, items  in configItems.iteritems():
      for item in items:
        if item.kind == 'filter':
          filters = mergedFilterSubItems.setdefault(item.name, {})
          filters[config] = item.subItems
        elif item.kind == 'file':
          configs = mergedFileItemConfigs.setdefault(item.filePath, [])
          configs.append(config)

    # Write out all of the <Filter> subitems first.
    filterNames = mergedFilterSubItems.keys()
    filterNames.sort()
    for name in filterNames:
      self.file.write('%s<Filter\n' % indent)
      self.file.write('%s\tName="%s"\n' % (indent, escapeAttr(name)))
      self.file.write('%s\t>' % indent)

      # Recurse on each filter's subitems
      filterSubItems = mergedFilterSubItems[name]
      self._writeSubItems(filterSubItems, indent + '\t')

      self.file.write('%s</Filter>\n' % indent)

    # Write out all of the <File> subitems
    filePaths = mergedFileItemConfigs.keys()
    filePaths.sort()
    for path in filePaths:
      configs = mergedFileItemConfigs[path]
      self.file.write('%s<File\n' % indent)
      self.file.write('%s\tRelativePath="%s"\n' % (indent, escapeAttr(path)))
      self.file.write('%s\t>\n' % indent)

      for config in self.configs:
        self.file.write('%s\t<FileConfiguration\n' % indent)
        self.file.write('%s\t\tName="%s"\n' % (
          indent,
          escapeAttr(config.name),
          ))

        # Exclude from build if file not present in this config
        if config not in configs:
          self.file.write('%s\t\tExcludedFromBuild="true"\n' % indent)
          
        self.file.write('%s\t\t>\n' % indent)
        self.file.write('%s\t\t<Tool\n' % indent)
        self.file.write('%s\t\t\tName="VCNMakeTool"\n' % indent)
        self.file.write('%s\t\t/>\n' % indent)
        self.file.write('%s\t</FileConfiguration>\n' % indent)
        
      self.file.write('%s</File>\n' % indent)

class MsvsSolutionGenerator(object):
  """I am the class that does the actual writing of solution files.
  """

  # Default member values
  file = None
  encoding = 'utf-8'
  version = '9.00' # Note: version is project version + 1
  
  def __init__(self, solution, registry):
    """Construct a new solution file writer.

    @param solutionFile: The Solution object containing details of solution
    file to build.
    
    @param registry: The ProjectRegistry to use to find details of referenced
    projects.
    """
    self.registry = registry
    self.solution = solution
    self.name = solution.name
    self.solutionDir = solution.dir
    self.solutionFilePath = solution.path
    
    self.solutionConfigurations = list(solution.configurations.values())
    self.solutionConfigurations.sort(key=lambda config: config.name)
    
    self.solutionGUID = generateGuid(self.solutionFilePath)

    # Construct a sorted list all project files
    projectFilePathToProject = {}
    for config in self.solutionConfigurations:
      for config in config.projectConfigurations:
        project = self.registry.getProjectByPath(config.path)
        if project is not None:
          projectConfig = project.configurations.get(config.name, None)
          if projectConfig is None:
            continue
          path = project.path
          projectFilePathToProject[path] = project
        else:
          print "Warning: skipping project %s (not built by cake)" % config.path
    projectFilePaths = projectFilePathToProject.keys()
    projectFilePaths.sort()
    self.projects = [projectFilePathToProject[p] for p in projectFilePaths]

  def getRelativePath(self, path):
    """Return path relative to the solution file.
    """
    return cake.path.relativePath(path, self.solutionDir)

  def build(self, engine):
    """Actually write the target file.
    """
    stream = StringIO.StringIO()
    self.file = codecs.getwriter(self.encoding)(stream)
    try:
      self.file.write(u"\ufeff\r\n") # BOM
      self.writeSolution()
    except:
      self.file.close()
      self.file = None
      raise
    newFileContents = stream.getvalue()
    self.file.close()
    self.file = None
      
    shouldBuild = engine.forceBuild
    if not shouldBuild:
      existingFileContents = None
      try:
        f = open(self.solutionFilePath, "rb")
        try:
          existingFileContents = f.read()
          shouldBuild = newFileContents != existingFileContents
        finally:
          f.close()
      except EnvironmentError:
        shouldBuild = True
    
    if shouldBuild:
      engine.logger.outputInfo("Generating Solution %s\n" % self.solutionFilePath)
      cake.filesys.makeDirs(self.solutionDir)
      open(self.solutionFilePath, "wb").write(newFileContents)
    else:
      engine.logger.outputDebug(
        "project",
        "Skipping Identical Solution %s\n" % self.solutionFilePath,
        )

  def writeSolution(self):
    """Write the solution part (this is essentially the whole file's contents)
    """
    self.writeHeader()
    self.writeProjectsSection()
    self.writeGlobalSection()

  def writeHeader(self):
    """Write the solution header.

    Visual Studio uses this to determine which version of the .sln format this is.
    """
    self.file.write(
      "Microsoft Visual Studio Solution File, Format Version %(version)s\r\n" % {
        'version' : self.version,
        }
      )
    self.file.write(
      "# Visual Studio 2005\r\n"
      )

  def writeProjectsSection(self):
    """Write the projects section.

    This section declares all of the constituent project files.
    """
    # Build a global list of all projects across all solution configurations
    for project in self.projects:
      self.writeProject(project)

  def writeProject(self, project):
    """Write details of an individual project.

    This associates an internal project guid with the visual studio project files
    and their external guids.
    """

    # Note: The external GUID must match up to that generated in the
    # .vcproj file. We could either just duplicate the logic here or
    # implement a parser that pulled the GUID from the .vcproj.
    # For now just duplicate logic (requires that all .vcproj files
    # are also generated by SCons).
    projectName = project.name
    externalGuid = project.externalGuid
    internalGuid = project.internalGuid

    projectFilePath = project.path
    relativePath = self.getRelativePath(projectFilePath)
    
    self.file.write('Project("%s") = "%s", "%s", "%s"\r\n' % (
      internalGuid, projectName, relativePath, externalGuid,
      ))
    self.file.write('EndProject\r\n')

  def writeGlobalSection(self):
    """Write all global sections.
    """
    self.file.write("Global\r\n")
    self.writeSourceCodeControlSection()
    self.writeSolutionConfigurationPlatformsSection()
    self.writeProjectConfigurationPlatformsSection()
    self.writeSolutionPropertiesSection()
    self.file.write("EndGlobal\r\n")

  def writeSourceCodeControlSection(self):
    """Write the section that defines the source code control for the projects.

    Looks up the MSVS_SCC_PROVIDER of the environment used to build the projects.
    """
    projectsWithScc = []
    
    for project in self.projects:
      if project.sccProvider is not None:
        projectsWithScc.append(project)

    if not projectsWithScc:
      return

    self.file.write("\tGlobalSection(SourceCodeControl) = preSolution\r\n")
    
    self.file.write(
      "\t\tSccNumberOfProjects = %i\r\n" % len(projectsWithScc)
      )

    i = 0
    for project in projectsWithScc:
      relativePath = self.getRelativePath(project.path)
      
      sccLocalPath = project.sccLocalPath
      if sccLocalPath is None:
        sccLocalPath = os.path.dirname(relativePath)
      
      sccProvider = project.sccProvider
      if sccProvider is None:
        sccProvider = ''

      sccProjectName = project.sccProjectName
      if sccProjectName is None:
        sccProjectName = project.name

      def escape(s):
        s = s.replace('\\', '\\\\')
        s = s.replace(' ', '\\u0020')
        return s

      self.file.write(
        "\t\tSccProjectUniqueName%(id)i = %(file_base)s\r\n"
        "\t\tSccProjectName%(id)i = %(scc_project_name)s\r\n"
        "\t\tSccLocalPath%(id)i = %(scc_local_path)s\r\n"
        "\t\tSccProvider%(id)i = %(scc_provider)s\r\n"
        "\t\tCanCheckoutShared = true\r\n"
        % {"id" : i,
           "file_base" : escape(relativePath),
           "scc_local_path" : escape(sccLocalPath),
           "scc_project_name" : escape(sccProjectName),
           "scc_provider" : escape(sccProvider),
           }
        )
      i += 1

    self.file.write(
      "\t\tSolutionUniqueID = %s\r\n" % self.solutionGUID
      )
    self.file.write("\tEndGlobalSection\r\n")

  def writeSolutionConfigurationPlatformsSection(self):
    
    if not self.solutionConfigurations:
      return

    self.file.write(
      "\tGlobalSection(SolutionConfigurationPlatforms) = preSolution\r\n"
      )

    # Make a list of all of the configs and platforms
    allConfigs = set()
    allPlatforms = set()
    allVariants = set()
    for solutionConfig in self.solutionConfigurations:
      config, platform = solutionConfig.name.split("|", 1)
      allConfigs.add(config)
      allPlatforms.add(platform)
      allVariants.add(solutionConfig.name)
      
    allConfigs = list(allConfigs)
    allConfigs.sort()
    allPlatforms = list(allPlatforms)
    allPlatforms.sort()
    allVariants = list(allVariants)
    allVariants.sort()

    for config in allConfigs:
      for platform in allPlatforms:
        variant = "%s|%s" % (config, platform)
        if variant in allVariants:
          actualVariant = variant
        else:
          # This variant doesn't exist, find a suitable variant that we
          # can map this one to.
          suffix = "|" + platform
          for candidateVariant in allVariants:
            if candidateVariant.endswith(suffix):
              actualVariant = candidateVariant
              break
            
        self.file.write("\t\t%s = %s\r\n" % (variant, actualVariant))

    self.file.write("\tEndGlobalSection\r\n")

  def writeProjectConfigurationPlatformsSection(self):

    self.file.write("\tGlobalSection(ProjectConfigurationPlatforms) = postSolution\r\n")

    for project in self.projects:
      guid = project.externalGuid
      for solutionConfig in self.solutionConfigurations:
        
        # Default the project variant to that of the solution...
        projectConfigName = solutionConfig.name
        
        # ...unless we know something more about the project's variants
        includeInBuild = True
#        includeInBuild = False
#        for config in solutionConfig.projectConfigurations:
#          projectConfigName = config.name
#          if config.path == project.path and config.name in project.configurations:
#            includeInBuild = config.activateProject
#            break
          
        # Map the solution config to the project config
        self.file.write(
          "\t\t%(guid)s.%(slnvariant)s.ActiveCfg = %(projvariant)s\r\n" %
          {"guid" : guid,
           "slnvariant" : solutionConfig.name,
           "projvariant" : projectConfigName,
           })

        # And optionally include in this solution config's build
        if includeInBuild:
          self.file.write(
            "\t\t%(guid)s.%(slnvariant)s.Build.0 = %(projvariant)s\r\n" %
          {"guid" : guid,
           "slnvariant" : solutionConfig.name,
           "projvariant" : projectConfigName,
           })
      
    self.file.write("\tEndGlobalSection\r\n")

  def writeSolutionPropertiesSection(self):
    self.file.write("\tGlobalSection(SolutionProperties) = preSolution\r\n")
    self.file.write("\t\tHideSolutionNode = FALSE\r\n")
    self.file.write("\tEndGlobalSection\r\n")
