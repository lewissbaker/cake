"""Project Tool.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license.
"""

import sys
import threading
import os.path
import codecs
import itertools
try:
  import cStringIO as StringIO
except ImportError:
  import StringIO

import cake.path
import cake.filesys
import cake.hash

from cake.target import FileTarget, getPath, getPaths
from cake.async import getResult, waitForAsyncResult, flatten
from cake.library import Tool
from cake.script import Script

try:
  from cake.library.compilers.msvc import MsvcCompiler
except ImportError:
  # This import will fail on platforms without the Windows registry.
  #
  # Given the tool can't be imported it can't be in use so the checking
  # performed below would never succeed.
  class MsvcCompiler(object):
    pass

class _Project(object):

  def __init__(self, path, filtersPath, name, version):

    self.path = path
    self.filtersPath = filtersPath
    self.dir = cake.path.dirName(path)
    self.name = name
    self.version = version
    self.sccProvider = None
    self.sccProjectName = None
    self.sccAuxPath = None
    self.sccLocalPath = None
    self.internalGuid = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"
    self.externalGuid = generateGuid(path)
    self.configurations = {}
    self.lock = threading.Lock()

  def addConfiguration(self, configuration):

    self.lock.acquire()
    try:
      key = (configuration.name, configuration.platform)
      if key in self.configurations:
        raise ValueError("Project '%s' already has configuration '%s-%s'." % (
            self.path,
            configuration.name,
            configuration.platform,
            ))
      self.configurations[key] = configuration
    finally:
      self.lock.release()

class _ProjectConfiguration(object):

  def __init__(
    self,
    name,
    platform,
    items,
    buildArgs,
    output,
    intermediateDir,
    buildLog,
    defines,
    includePaths,
    assemblyPaths,
    forcedIncludes,
    forcedUsings,
    compileAsManaged,
    additionalOptions,
    localDebuggerEnvironment,
    ):

    self.name = name
    self.platform = platform
    self.items = items
    self.buildArgs = buildArgs
    self.output = output
    self.intermediateDir = intermediateDir
    self.buildLog = buildLog
    self.defines = defines
    self.includePaths = includePaths
    self.assemblyPaths = assemblyPaths
    self.forcedIncludes = forcedIncludes
    self.forcedUsings = forcedUsings
    self.compileAsManaged = compileAsManaged
    self.additionalOptions = additionalOptions
    self.localDebuggerEnvironment = localDebuggerEnvironment

class _Solution(object):

  def __init__(self, path, version):

    self.path = path
    self.dir = cake.path.dirName(path)
    self.name = cake.path.baseNameWithoutExtension(path)
    self.version = version
    self.configurations = {}
    self.lock = threading.Lock()

  def addConfiguration(self, configuration):

    self.lock.acquire()
    try:
      key = (configuration.name, configuration.platform)
      if key in self.configurations:
        raise ValueError("Solution '%s' already has configuration '%s-%s'." % (
            self.path,
            configuration.name,
            configuration.platform,
            ))
      self.configurations[key] = configuration
    finally:
      self.lock.release()

class _SolutionConfiguration(object):

  def __init__(self, name, platform):

    self.name = name
    self.platform = platform
    self.projectConfigurations = []

  def addProjectConfiguration(self, configuration):

    self.projectConfigurations.append(configuration)

class _SolutionProjectConfiguration(object):

  def __init__(self, name, platform, path, build):

    self.name = name
    self.platform = platform
    self.path = path
    self.build = build

class _ProjectRegistry(object):

  def __init__(self):

    self.projects = {}
    self.lock = threading.Lock()

  def getProject(self, path, filtersPath, name, version):

    key = os.path.normpath(os.path.normcase(path))
    self.lock.acquire()
    try:
      project = self.projects.get(key, None)
      if project is None:
        project = _Project(path, filtersPath, name, version)
        self.projects[key] = project
      return project
    finally:
      self.lock.release()

  def getProjectByPath(self, path):

    key = os.path.normpath(os.path.normcase(path))
    return self.projects.get(key, None)

class _SolutionRegistry(object):

  def __init__(self):

    self.solutions = {}
    self.lock = threading.Lock()

  def getSolution(self, path, version):

    key = os.path.normpath(os.path.normcase(path))
    self.lock.acquire()
    try:
      solution = self.solutions.get(key, None)
      if solution is None:
        solution = _Solution(path, version)
        self.solutions[key] = solution
      return solution
    finally:
      self.lock.release()

class ProjectToolTarget(FileTarget):
  """A target returned by the ProjectTool.

  @ivar tool: The tool instance that generated this file target.
  @type tool: L{Tool}
  """
  def __init__(self, path, task, tool):
    FileTarget.__init__(self, path, task)
    self.tool = tool

class ProjectTarget(ProjectToolTarget):
  """A project target.

  @ivar project: The project file target.
  @type project: L{FileTarget}
  @ivar filters: An optional file target for the associated '.filters' file.
  @type filters: L{FileTarget}
  """
  def __init__(self, path, task, tool, filters):
    ProjectToolTarget.__init__(self, path, task, tool)
    self.project = FileTarget(path, task)
    if filters is None:
      self.filters = None
    else:
      self.filters = FileTarget(filters, task)

class SolutionTarget(ProjectToolTarget):
  """A solution target.

  @ivar solution: The solution file target.
  @type solution: L{FileTarget}
  """
  def __init__(self, path, task, tool):
    ProjectToolTarget.__init__(self, path, task, tool)
    self.solution = FileTarget(path, task)

class ProjectTool(Tool):
  """Tool that provides project/solution generation capabilities.
  """

  projectConfigName = None
  """The project config name.

  This should be set to a string that uniquely identifies the project
  configuration, eg. 'Windows (x86) Debug (msvc)' or
  'PS3 (spu) Release (gcc)'.
  """
  projectPlatformName = None
  """The project platform name.

  For Visual Studio this should be set to one of 'Win32', 'Xbox'
  or 'Xbox 360' depending on the platform you are compiling for.
  """
  solutionConfigName = None
  """The solution config name.

  This should be set to a string that identifies the solution
  configuration, eg. 'Debug' or 'Release'.
  """
  solutionPlatformName = None
  """The solution platform name.

  This should be set to a string that identifies the solution
  platform, eg. 'Windows Msvc (x86)' or 'PS3 Gcc (spu)'.
  """

  VS2002 = 0
  """Visual Studio .NET 2002
  """
  VS2003 = 1
  """Visual Studio .NET 2003
  """
  VS2005 = 2
  """Visual Studio 2005
  """
  VS2008 = 3
  """Visual Studio 2008
  """
  VS2010 = 4
  """Visual Studio 2010
  """
  VS2015 = 5

  product = VS2015
  """The product to generate solutions and projects for.

  Can be one of L{VS2002}, L{VS2003}, L{VS2005}, L{VS2008}, L{VS2010} or L{VS2015}.
  @type: enum
  """

  localDebuggerEnvironment = '$(LocalDebuggerEnvironment)'
  """Defines the environment used when using the local debugger.
  This should be in the form VARIABLE=VALUE where each variable is
  defined on a new line.

  Only applicable for L{VS2010} or L{VS2015}

  @type: string
  """

  class SolutionProjectItem(object):
    """A class used to further define solution project items.

    This class can be used to wrap solution project items to
    further define their attributes such as::
      project.solution(
        projects = [
          project.SolutionProjectItem(
            "MyProject",
            build=False, # This project won't build when the solution is built.
            ),
          ],
        target="MySolution",
        )
    """

    build = True
    """Whether the project should be built as part of a solution build.
    @type: bool
    """

    def __init__(self, project, **kwargs):
      self.project = project
      for k, v in kwargs.iteritems():
        setattr(self, k, v)

  _projects = _ProjectRegistry()
  _solutions = _SolutionRegistry()

  _msvsBuildLogSuffix = '.html'
  _msvsBuildLogSuffix2010 = '.log'
  _msvsProjectSuffix = '.vcproj'
  _msvsProjectSuffix2010 = '.vcxproj'
  _msvsFiltersSuffix2010 = '.filters'
  _msvsSolutionSuffix = '.sln'

  _toProjectVersion = {
    VS2002 : "7.00",
    VS2003 : "7.10",
    VS2005 : "8.00",
    VS2008 : "9.00",
    VS2010 : "4.0", # MSBuild script
    VS2015 : "14.0", # MSBuild script
    }

  _toSolutionVersion = {
    VS2002 : '7.00',
    VS2003 : '8.00',
    VS2005 : '9.00',
    VS2008 : '10.00',
    VS2010 : '11.00',
    VS2015 : '12.00',
    }

  def __init__(self, configuration):
    Tool.__init__(self, configuration)

  def _getProjectConfigName(self):

    configName = self.projectConfigName
    if configName is None:
      keywords = Script.getCurrent().variant.keywords
      configName = " ".join(keywords.values())
    return configName

  def _getProjectPlatformName(self):

    platformName = self.projectPlatformName
    if platformName is None:
      platformName = "Win32"
    return platformName

  def _getSolutionConfigName(self):

    configName = self.solutionConfigName
    if configName is None:
      keywords = Script.getCurrent().variant.keywords
      configName = " ".join(keywords.values())
    return configName

  def _getSolutionPlatformName(self):

    platformName = self.solutionPlatformName
    if platformName is None:
      platformName = "Win32"
    return platformName

  def project(
    self,
    target,
    items=None,
    output=None,
    name=None,
    intermediateDir=None,
    buildLog=None,
    compiler=None,
    buildTargets=None,
    **kwargs
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
    @param output: The output file that this project generates.
    This file will also be the executable used for debugging purposes
    (if applicable).
    @type output: L{CompilerTarget}
    @param name: The name of the generated project. If this is None the
    base filename of the target is used instead.
    @type name: string
    @param intermediateDir: The path to intermediate files. If this is
    None the directory of the first output is used instead.
    @type intermediateDir: string
    @param buildLog: The path to the build log file that MSVS will
    generate for each build. If this is None the name of the first output
    is used instead.
    @type buildLog: string
    @param compiler: A compiler tool containing the compile settings
    used for the aid of intellisense. If not supplied the compiler is
    obtained implicitly via 'ouput.compiler'.
    @type compiler: L{cake.library.compilers.Compiler} or C{None}
    @param buildTargets: A collection of build targets to build when
    building the project from within Visual Studio.
    @type buildTargets: list of L{cake.target.Target}

    @return: A L{FileTarget} that specifies the full path to the
    generated project file (with extension if applicable).
    @rtype: L{FileTarget}
    """
    tool = self.clone()
    for k, v in kwargs.iteritems():
      setattr(tool, k, v)

    basePath = self.configuration.basePath

    target = basePath(target)
    items = basePath(items)
    output = basePath(output)
    intermediateDir = basePath(intermediateDir)
    buildLog = basePath(buildLog)

    return tool._project(
      target,
      items,
      output,
      name,
      intermediateDir,
      buildLog,
      compiler,
      buildTargets,
      )

  def _project(
    self,
    target,
    items=None,
    output=None,
    name=None,
    intermediateDir=None,
    buildLog=None,
    compiler=None,
    buildTargets=None,
    ):

    # Project name defaults the base filename without extension
    if items is None:
      items = []

    if name is None:
      name = cake.path.baseNameWithoutExtension(target)

    projectBuildTargetName = name + "_vsbuild"
    script = Script.getCurrentRoot()
    projectBuildTarget = script.getTarget(projectBuildTargetName)

    if buildTargets is not None:
      projectBuildTarget.addTargets(buildTargets)
    elif output is None:
      projectBuildTarget.addTarget(script.getDefaultTarget())
    else:
      @waitForAsyncResult
      def addTarget(output):
        if isinstance(output, cake.target.Target):
          projectBuildTarget.addTarget(output)
      addTarget(output)

    if self.product >= self.VS2010:
      target = cake.path.forceExtension(target, self._msvsProjectSuffix2010)
      filters = cake.path.forceExtension(target, self._msvsFiltersSuffix2010)
    else:
      target = cake.path.forceExtension(target, self._msvsProjectSuffix)
      filters = None

    @waitForAsyncResult
    def run(output, items, intermediateDir=intermediateDir, buildLog=buildLog, compiler=compiler):
      if compiler is None and output is not None:
        try:
          compiler = output.compiler
        except AttributeError:
          pass

      if output is not None:
        outputPath = output.path
      else:
        outputPath = target

      if compiler is not None:
        defines = compiler.getDefines()
        includePaths = compiler.getIncludePaths()
        forcedIncludes = compiler.getForcedIncludes()
        forcedUsings = getPaths(getattr(compiler, "forcedUsings", []))
      else:
        defines = []
        includePaths = []
        forcedIncludes = []
        forcedUsings = []

      if isinstance(compiler, MsvcCompiler):
        additionalOptions = list(compiler.cppFlags)
      else:
        additionalOptions = []

      # TODO: Fill these out when the compiler has them.
      compileAsManaged = ""
      assemblyPaths = []

      # Intermediate dir defaults to the output dir
      if intermediateDir is None:
        intermediateDir = cake.path.dirName(outputPath)

      # Build log defaults to the output path
      if self.product >= self.VS2010:
        if buildLog is None:
          buildLog = cake.path.stripExtension(outputPath)
        buildLog = cake.path.forceExtension(buildLog, self._msvsBuildLogSuffix2010)
      else:
        if buildLog is None:
          buildLog = cake.path.stripExtension(outputPath) + ".buildlog"
        buildLog = cake.path.forceExtension(buildLog, self._msvsBuildLogSuffix)

      script = Script.getCurrent()
      configuration = script.configuration
      configName = self._getProjectConfigName()
      platformName = self._getProjectPlatformName()

      # Construct the build args
      targetDir = configuration.abspath(cake.path.dirName(target))
      pythonExe = cake.path.absPath(sys.executable, self.engine.oscwd)
      cakeScript = cake.path.absPath(sys.argv[0], self.engine.oscwd)
      scriptPath = configuration.abspath(script.path)
      keywords = script.variant.keywords

      # It's possible these files were passed relative to some arbitrary
      # directory so make sure they exist.
      if not cake.path.isFile(pythonExe):
        raise EnvironmentError("Could not find Python executable at: '%s'" % pythonExe)
      if not cake.path.isFile(cakeScript):
        raise EnvironmentError("Could not find Cake script at: '%s'" % cakeScript)

      scriptArg = cake.path.relativePath(scriptPath, targetDir)
      scriptArg += "@" + projectBuildTargetName

      buildArgs = [
        pythonExe,
        "-u",
        cake.path.relativePath(cakeScript, targetDir),
        scriptArg,
        ]

      # Propgate the option (at the time of project generation) to suppress
      # bytecode files when building from the projects.
      if sys.dont_write_bytecode:
        buildArgs.insert(1, "-B")

      buildArgs.extend("=".join([k, v]) for k, v in keywords.iteritems())

      try:
        version = self._toProjectVersion[self.product]
      except KeyError:
        raise ValueError("Unknown product: '%d'" % self.product)

      project = self._projects.getProject(target, filters, name, version)
      project.addConfiguration(_ProjectConfiguration(
        configName,
        platformName,
        items,
        buildArgs,
        outputPath,
        intermediateDir,
        buildLog,
        defines,
        includePaths,
        assemblyPaths,
        forcedIncludes,
        forcedUsings,
        compileAsManaged,
        additionalOptions,
        self.localDebuggerEnvironment,
        ))

    if self.enabled:
      run(output, items)

    return ProjectTarget(path=target, task=None, tool=self, filters=filters)

  def solution(self, target, projects, **kwargs):
    """Generate a solution file.

    @param target: The path for the generated solution file. If this path
    doesn't have the correct suffix it will be appended automatically.
    @type target: string
    @param projects: A list of projects to include in the solution. If
    any of the projects listed don't have the correct suffix it will be
    appended automatically.
    @type projects: list of string
    """
    tool = self.clone()
    for k, v in kwargs.iteritems():
      setattr(tool, k, v)

    basePath = self.configuration.basePath

    target = basePath(target)
    projects = basePath(projects)

    return tool._solution(target, projects)

  def _solution(self, target, projects):

    # Obtain these now because they may rely on the value of Script.getCurrent()
    configName = self._getSolutionConfigName()
    platformName = self._getSolutionPlatformName()
    projectConfigName = self._getProjectConfigName()
    projectPlatformName = self._getProjectPlatformName()

    @waitForAsyncResult
    def run(target, projects):
      target = cake.path.forceExtension(target, self._msvsSolutionSuffix)

      if not self.enabled:
        return FileTarget(path=target, task=None)

      try:
        version = self._toSolutionVersion[self.product]
      except KeyError:
        raise ValueError("Unknown product: '%d'" % self.product)

      solution = self._solutions.getSolution(target, version)
      configuration = _SolutionConfiguration(
        configName,
        platformName,
        )
      solution.addConfiguration(configuration)

      if self.product >= self.VS2010:
        projectExtension = self._msvsProjectSuffix2010
      else:
        projectExtension = self._msvsProjectSuffix

      for p in projects:
        if not isinstance(p, self.SolutionProjectItem):
          p = self.SolutionProjectItem(p)

        projectPath = getPath(p.project)
        projectPath = cake.path.forceExtension(projectPath, projectExtension)

        configuration.addProjectConfiguration(_SolutionProjectConfiguration(
          projectConfigName,
          projectPlatformName,
          projectPath,
          p.build,
          ))

      return SolutionTarget(path=target, task=None, tool=self)

    return run(target, flatten(projects))

  def build(self):
    """Build project and solution files.

    This function will actually write the project and solution files,
    provided the files on disk are different to the files being written.
    If the engine.forceBuild flag is set to True the files will be written
    regardless of any differences.

    @param configuration: The configuration to resolve paths with.
    @type configuration: L{cake.engine.Configuration}
    """
    if not self.enabled:
      return

    # Generate solutions first as they will attempt to reload in Visual
    # studio and automatically reload all changed projects too. This
    # saves having to click reload on every project change (most of
    # the time).
    for solution in self._solutions.solutions.values():
      generator = MsvsSolutionGenerator(self.configuration, solution, self._projects)
      generator.build()

    for project in self._projects.projects.values():
      if project.version in ('4.0', '14.0'):
        generator = MsBuildProjectGenerator(self.configuration, project)
        generator.build()
        generator = MsBuildFiltersGenerator(self.configuration, project)
        generator.build()
      else:
        generator = MsvsProjectGenerator(self.configuration, project)
        generator.build()

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

def convertToProjectItems(configuration, srcfiles, projectDir):
  """Convert the dictionary-based datastructure for defining project items
  and filters into ProjectItem objects.

  @param srcfiles: A dictionary mapping filter names to either a list of
  files or to a similar dictionary. An empty sub-item name in the dictionary
  indicates that the sub-item list should be added to the parent's sub-items.
  eg. Passing this structure::
     {'Sources' :
       {'Private' : ['fooimpl.cpp', 'barimpl.cpp'],
        '' : ['foo.cpp'],
        },
       'Headers' : ['foo.h'],
       '' : ['source.cake'],
       }

  will return this hierarchy of items::
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
  abspath = configuration.abspath
  if isinstance(srcfiles, dict):
    for name in srcfiles:
      subItems = convertToProjectItems(configuration, srcfiles[name], projectDir)
      if name:
        filterNode = ProjectFilterItem(name)
        filterNode.addSubItems(subItems)
        results.append(filterNode)
      else:
        results.extend(subItems)
  elif isinstance(srcfiles, (list, set, tuple)):
    for srcfile in flatten(srcfiles):
      filePath = getPath(srcfile)
      relPath = cake.path.relativePath(abspath(filePath), abspath(projectDir))
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

def _writeIt(generator, target):
  """Write the contents of a project or solution file only if the target
  file is out of date.
  """
  configuration = generator.configuration
  engine = configuration.engine
  type = generator.type

  stream = StringIO.StringIO()
  writer = codecs.getwriter(generator.encoding)(stream)
  try:
    generator._writeContents(writer)
  except:
    writer.close()
    raise
  newFileContents = stream.getvalue()
  writer.close()

  # Check the existing dependency info file
  buildArgs = []
  _, reasonToBuild = configuration.checkDependencyInfo(target, buildArgs)

  absTarget = configuration.abspath(target)
  if reasonToBuild is None:
    # Compare new file contents against existing file
    existingFileContents = None
    try:
      existingFileContents = cake.filesys.readFile(absTarget)
      if newFileContents != existingFileContents:
        reasonToBuild = "it has been changed"
    except EnvironmentError:
      reasonToBuild = "it doesn't exist"

  if reasonToBuild is not None:
    engine.logger.outputDebug(
      "reason",
      "Rebuilding '" + target + "' because " + reasonToBuild + ".\n",
      )
    engine.logger.outputInfo("Generating %s %s\n" % (type, target))
    cake.filesys.writeFile(absTarget, newFileContents)

    # Now that the file has been written successfully, save the new dependency file
    newDependencyInfo = configuration.createDependencyInfo(
      targets=[target],
      args=buildArgs,
      dependencies=[],
      )
    configuration.storeDependencyInfo(newDependencyInfo)
  else:
    engine.logger.outputDebug(
      "project",
      "Skipping Identical %s %s\n" % (type, target),
      )

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
\t\t\t\tReBuildCommandLine="%(rebuildcmd)s"
\t\t\t\tCleanCommandLine="%(cleancmd)s"
\t\t\t\tOutput="%(runfile)s"
\t\t\t\tPreprocessorDefinitions="%(defines)s"
\t\t\t\tIncludeSearchPath="%(includes)s"
\t\t\t\tForcedIncludes="%(forcedinc)s"
\t\t\t\tAssemblySearchPath="%(asspath)s"
\t\t\t\tForcedUsingAssemblies="%(forceduse)s"
\t\t\t\tCompileAsManaged="%(compmanag)s"
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
  encoding = 'utf-8'
  type = "Project"

  def __init__(self, configuration, project):
    """Construct a new project generator instance.

    @param project: A Project object containing all info required for the project.
    """
    self.configuration = configuration
    self.project = project
    self.projectName = project.name
    self.projectDir = project.dir
    self.projectFilePath = project.path
    self.version = project.version
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
    self.platforms = list(frozenset(c.platform for c in self.configs))
    self.platforms.sort()

  def build(self):
    """Create and write the .vcproj file.

    Throws an exception if building the project file fails.
    """
    _writeIt(self, self.projectFilePath)

  def getRelativePath(self, path):
    """Return path relative to the project file.
    """
    abspath = self.configuration.abspath
    return cake.path.relativePath(abspath(path), abspath(self.projectDir))

  def _writeContents(self, writer):
    """Write the project to the currently open file.
    """
    self._writeProjectHeader(writer)
    self._writePlatforms(writer)
    self._writeConfigurations(writer)
    self._writeFiles(writer)
    self._writeProjectTailer(writer)

  def _writeProjectHeader(self, writer):
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

    writer.write(_msvsProjectHeader % {
      'encoding' : escapeAttr(self.encoding),
      'version' : escapeAttr(self.version),
      'name' : escapeAttr(self.projectName),
      'guid' : escapeAttr(guid),
      'scc_attrs' : scc_attrs,
      })

  def _writeProjectTailer(self, writer):
    """Write the project tailer to the file.

    This should be the last content written to the file as it closes off
    datastructures written by the header.
    """
    writer.write(_msvsProjectTailer)

  def _writePlatforms(self, writer):
    """Write the section that declares all of the platforms supported by this
    project.
    """
    writer.write("\t<Platforms>\n")
    for platform in self.platforms:
      writer.write('\t\t<Platform\n')
      writer.write('\t\t\tName="%s"\n' % escapeAttr(platform))
      writer.write('\t\t/>\n')
    writer.write("\t</Platforms>\n")

  def _writeConfigurations(self, writer):
    """Write the section that declares all of the configurations supported by
    this project.
    """
    writer.write("\t<Configurations>\n")
    for config in self.configs:
      self._writeConfiguration(writer, config)
    writer.write("\t</Configurations>\n")

  def _writeConfiguration(self, writer, config):
    """Write a section that declares an individual build configuration.
    """
    outdir = self.getRelativePath(os.path.dirname(config.output))
    intdir = self.getRelativePath(config.intermediateDir)
    runfile = self.getRelativePath(config.output)
    buildlog = self.getRelativePath(config.buildLog)

    includePaths = [self.getRelativePath(p) for p in config.includePaths]
    assemblyPaths = [self.getRelativePath(p) for p in config.assemblyPaths]
    forcedIncludes = [self.getRelativePath(p) for p in config.forcedIncludes]

    includePaths = ';'.join(includePaths)
    assemblyPaths = ';'.join(assemblyPaths)
    forcedIncludes = ';'.join(forcedIncludes)
    forcedUsings = ';'.join(config.forcedUsings)
    compileAsManaged = config.compileAsManaged

    defines = ';'.join(config.defines)
    name = "%s|%s" % (config.name, config.platform)

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
    cleanCmd = "@"
    rebuildCmd = buildCmd + " -f"

    writer.write(_msvsProjectConfigurationHeader % {
      'name' : escapeAttr(name),
      'outdir' : escapeAttr(outdir),
      'intdir' : escapeAttr(intdir),
      'buildlog' : escapeAttr(buildlog),
      })

    writer.write(_msvsProjectConfigurationMakeTool % {
      'buildcmd' : escapeAttr(buildCmd),
      'rebuildcmd' : escapeAttr(rebuildCmd),
      'cleancmd' : escapeAttr(cleanCmd),
      'runfile' : escapeAttr(runfile),
      'defines' : escapeAttr(defines),
      'includes' : escapeAttr(includePaths),
      'forcedinc' : escapeAttr(forcedIncludes),
      'asspath' : escapeAttr(assemblyPaths),
      'forceduse' : escapeAttr(forcedUsings),
      'compmanag' : escapeAttr(compileAsManaged),
      })

    if config.name.endswith("|Xbox 360"):
      writer.write(_msvsProjectConfigurationXboxDeploymentTool)

    writer.write(_msvsProjectConfigurationTailer)

  def _writeFiles(self, writer):

    configItems = {}
    for config in self.configs:
      configItems[config] = convertToProjectItems(
        self.configuration,
        config.items,
        self.projectDir,
        )

    writer.write("\t<Files>\n")
    self._writeSubItems(writer, configItems, indent='\t\t')
    writer.write("\t</Files>\n")

  def _writeSubItems(self, writer, configItems, indent):
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
      writer.write('%s<Filter\n' % indent)
      writer.write('%s\tName="%s"\n' % (indent, escapeAttr(name)))
      writer.write('%s\t>' % indent)

      # Recurse on each filter's subitems
      filterSubItems = mergedFilterSubItems[name]
      self._writeSubItems(writer, filterSubItems, indent + '\t')

      writer.write('%s</Filter>\n' % indent)

    # Write out all of the <File> subitems
    filePaths = mergedFileItemConfigs.keys()
    filePaths.sort()
    for path in filePaths:
      configs = mergedFileItemConfigs[path]
      writer.write('%s<File\n' % indent)
      writer.write('%s\tRelativePath="%s"\n' % (indent, escapeAttr(path)))
      writer.write('%s\t>\n' % indent)

      for config in self.configs:
        writer.write('%s\t<FileConfiguration\n' % indent)
        writer.write('%s\t\tName="%s"\n' % (
          indent,
          escapeAttr(config.name),
          ))

        # Exclude from build if file not present in this config
        if config not in configs:
          writer.write('%s\t\tExcludedFromBuild="true"\n' % indent)

        writer.write('%s\t\t>\n' % indent)
        writer.write('%s\t\t<Tool\n' % indent)
        writer.write('%s\t\t\tName="VCNMakeTool"\n' % indent)
        writer.write('%s\t\t/>\n' % indent)
        writer.write('%s\t</FileConfiguration>\n' % indent)

      writer.write('%s</File>\n' % indent)

_msbuildProjectHeader = """\
<?xml version="1.0" encoding="%(encoding)s"?>
<Project\
 DefaultTargets="Build"\
 ToolsVersion="%(version)s"\
 xmlns="http://schemas.microsoft.com/developer/msbuild/2003"\
>
"""
_msbuildProjectTailer = """\
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets">
  </ImportGroup>
</Project>
"""

_msbuildProjectConfiguration = """\
    <ProjectConfiguration Include="%(name)s|%(platform)s">
      <Configuration>%(name)s</Configuration>
      <Platform>%(platform)s</Platform>
    </ProjectConfiguration>
"""

_msbuildGlobals = """\
  <PropertyGroup Label="Globals">
    <ProjectGuid>%(guid)s</ProjectGuid>
    <Keyword>MakeFileProj</Keyword>
  </PropertyGroup>
"""

_msbuildConfigurationTypesHeader = """\
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.Default.props" />
"""

_msbuildConfigurationTypesTailer = """\
  <Import Project="$(VCTargetsPath)\Microsoft.Cpp.props" />
  <ImportGroup Label="ExtensionSettings">
  </ImportGroup>
"""

_msbuildConfigurationType = """\
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(platform)s'" Label="Configuration">
    <ConfigurationType>Makefile</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <OutDir>%(outdir)s</OutDir>
    <IntDir>%(intdir)s</IntDir>
    <LocalDebuggerEnvironment>%(localdebuggerenvironment)s</LocalDebuggerEnvironment>
  </PropertyGroup>
"""

_msbuildConfigurationPropertySheet = """\
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(platform)s'">
    <Import Project="$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
"""

_msbuildConfiguration = """\
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(platform)s'">
    <NMakeBuildCommandLine>%(buildcmd)s</NMakeBuildCommandLine>
    <NMakeOutput>%(output)s</NMakeOutput>
    <NMakeCleanCommandLine>%(cleancmd)s</NMakeCleanCommandLine>
    <NMakeReBuildCommandLine>%(rebuildcmd)s</NMakeReBuildCommandLine>
    <NMakePreprocessorDefinitions>%(defines)s</NMakePreprocessorDefinitions>
    <NMakeIncludeSearchPath>%(includepaths)s</NMakeIncludeSearchPath>
    <NMakeForcedIncludes>%(forcedincludes)s</NMakeForcedIncludes>
    <NMakeAssemblySearchPath>%(assemblypaths)s</NMakeAssemblySearchPath>
    <NMakeForcedUsingAssemblies>%(forcedusings)s</NMakeForcedUsingAssemblies>
    <AdditionalOptions>%(additionaloptions)s</AdditionalOptions>
  </PropertyGroup>
"""

_msbuildLog = """\
  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='%(name)s|%(platform)s'">
    <BuildLog>
      <Path>%(buildlog)s</Path>
    </BuildLog>
  </ItemDefinitionGroup>
"""

_msbuildExcludedFile = """\
      <ExcludedFromBuild Condition="'$(Configuration)|$(Platform)'=='%(config)s|%(platform)s'">true</ExcludedFromBuild>
"""

class MsBuildProjectGenerator(object):
  """I am a class that is able to generate a single .vcproj file from
  its configuration information.
  """

  # Default member values
  encoding = 'utf-8'
  type = "Project"

  def __init__(self, configuration, project):
    """Construct a new project generator instance.

    @param project: A Project object containing all info required for the project.
    """
    self.configuration = configuration
    self.project = project
    self.projectName = project.name
    self.projectDir = project.dir
    self.projectFilePath = project.path
    self.version = project.version
    self.configs = project.configurations.values()

  def build(self):
    """Create and write the .vcproj file.

    Throws an exception if building the project file fails.
    """
    _writeIt(self, self.projectFilePath)

  def getRelativePath(self, path):
    """Return path relative to the project file.
    """
    abspath = self.configuration.abspath
    return cake.path.relativePath(abspath(path), abspath(self.projectDir))

  def _writeContents(self, writer):
    """Write the project to the currently open file.
    """
    self._writeProjectHeader(writer)
    self._writeProjectConfigurations(writer)
    self._writeGlobals(writer)
    self._writeConfigurationTypes(writer)
    self._writeConfigurations(writer)
    self._writeBuildLogs(writer)
    self._writeFiles(writer)
    self._writeProjectTailer(writer)

  def _writeProjectHeader(self, writer):
    """Write the project header section to the currently open file.

    This should be written at the start of the file.
    """
    writer.write(_msbuildProjectHeader % {
      "encoding" : escapeAttr(self.encoding),
      "version" : escapeAttr(self.version),
      })

  def _writeProjectTailer(self, writer):
    """Write the project tailer to the file.

    This should be the last content written to the file as it closes off
    datastructures written by the header.
    """
    writer.write(_msbuildProjectTailer)

  def _writeProjectConfigurations(self, writer):
    """Write the section that declares all of the configurations supported by
    this project.
    """
    writer.write('  <ItemGroup Label="ProjectConfigurations">\n')
    for config in self.configs:
      self._writeProjectConfiguration(writer, config)
    writer.write("  </ItemGroup>\n")

  def _writeProjectConfiguration(self, writer, config):
    """Write a section that declares an individual build configuration.
    """
    writer.write(_msbuildProjectConfiguration % {
      "name" : escapeAttr(config.name),
      "platform" : escapeAttr(config.platform),
      })

  def _writeGlobals(self, writer):
    """Write a section that declares globals.
    """
    guid = self.project.externalGuid

    writer.write(_msbuildGlobals % {
      "guid" : escapeAttr(guid),
      })

  def _writeConfigurationTypes(self, writer):
    """Write the section that declares all of the configurations supported by
    this project.
    """
    writer.write(_msbuildConfigurationTypesHeader)
    for config in self.configs:
      self._writeConfigurationType(writer, config)
    writer.write(_msbuildConfigurationTypesTailer)
    for config in self.configs:
      self._writeConfigurationPropertySheet(writer, config)
    writer.write('  <PropertyGroup Label="UserMacros" />\n')

  def _writeConfigurationType(self, writer, config):
    """Write a section that declares an individual build configuration.
    """
    outdir = self.getRelativePath(os.path.dirname(config.output))
    intdir = self.getRelativePath(config.intermediateDir)

    writer.write(_msbuildConfigurationType % {
      "name" : escapeAttr(config.name),
      "platform" : escapeAttr(config.platform),
      "outdir" : escapeAttr(outdir),
      "intdir" : escapeAttr(intdir),
      "localdebuggerenvironment" : escapeAttr(config.localDebuggerEnvironment),
      })

  def _writeConfigurationPropertySheet(self, writer, config):
    """Write a section that declares an individual build configuration.
    """
    writer.write(_msbuildConfigurationPropertySheet % {
      "name" : escapeAttr(config.name),
      "platform" : escapeAttr(config.platform),
      })

  def _writeConfigurations(self, writer):
    """Write the section that declares all of the configurations supported by
    this project.
    """
    for config in self.configs:
      self._writeConfiguration(writer, config)

  def _writeConfiguration(self, writer, config):
    """Write a section that declares an individual build configuration.
    """
    output = self.getRelativePath(config.output)

    includePaths = [self.getRelativePath(p) for p in config.includePaths]
    assemblyPaths = [self.getRelativePath(p) for p in config.assemblyPaths]

    includePaths = ';'.join(includePaths + ['$(NMakeIncludeSearchPath)'])
    assemblyPaths = ';'.join(assemblyPaths + ['$(NMakeAssemblySearchPath)'])
    forcedIncludes = ';'.join(itertools.chain(config.forcedIncludes, ['$(NMakeForcedIncludes)']))
    forcedUsings = ';'.join(itertools.chain(config.forcedUsings, ['$(NMakeForcedUsingAssemblies)']))
    defines = ';'.join(itertools.chain(config.defines, ['$(NMakePreprocessorDefinitions)']))
    additionalOptions = ' '.join(config.additionalOptions)

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
    cleanCmd = "@"
    rebuildCmd = buildCmd + " -f"

    writer.write(_msbuildConfiguration % {
      "name" : escapeAttr(config.name),
      "platform" : escapeAttr(config.platform),
      "buildcmd" : escapeAttr(buildCmd),
      "output" : escapeAttr(output),
      "cleancmd" : escapeAttr(cleanCmd),
      "rebuildcmd" : escapeAttr(rebuildCmd),
      "defines" : escapeAttr(defines),
      "includepaths" : escapeAttr(includePaths),
      "forcedincludes" : escapeAttr(forcedIncludes),
      "assemblypaths" : escapeAttr(assemblyPaths),
      "forcedusings" : escapeAttr(forcedUsings),
      "additionaloptions": escapeAttr(additionalOptions),
      })

  def _writeBuildLogs(self, writer):
    """Write the section that declares all of the configurations supported by
    this project.
    """
    for config in self.configs:
      self._writeBuildLog(writer, config)

  def _writeBuildLog(self, writer, config):
    """Write a section that declares an individual build configuration.
    """
    buildLog = self.getRelativePath(config.buildLog)

    writer.write(_msbuildLog % {
      "name" : escapeAttr(config.name),
      "platform" : escapeAttr(config.platform),
      "buildlog" : escapeAttr(buildLog),
      })

  def _writeFiles(self, writer):

    configItems = {}
    for config in self.configs:
      configItems[config] = convertToProjectItems(
        self.configuration,
        config.items,
        self.projectDir,
        )

    writer.write('  <ItemGroup>\n')
    self._writeSubFiles(writer, configItems)
    writer.write('  </ItemGroup>\n')

  def _writeSubFiles(self, writer, configItems, parent=None):
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
      if parent:
        path = parent + "\\" + name
      else:
        path = name

      # Recurse on each filter's subitems
      filterSubItems = mergedFilterSubItems[name]
      self._writeSubFiles(writer, filterSubItems, path)

    # Write out all of the <File> subitems
    filePaths = mergedFileItemConfigs.keys()
    filePaths.sort()
    for path in filePaths:
      configs = mergedFileItemConfigs[path]

      excluded = False
      for config in self.configs:
        if config not in configs:
          excluded = True
          break

      if excluded:
        writer.write('    <None Include="%(name)s">\n' % {
          "name" : escapeAttr(path),
          })
        for config in self.configs:
          if config not in configs:
            writer.write(_msbuildExcludedFile % {
              "config" : escapeAttr(config.name),
              "platform" : escapeAttr(config.platform),
              })
        writer.write('    </None>\n')
      else:
        writer.write('    <None Include="%(name)s" />\n' % {
          "name" : escapeAttr(path),
          })

_msbuildFiltersHeader = """\
<?xml version="1.0" encoding="%(encoding)s"?>
<Project\
 ToolsVersion="%(version)s"\
 xmlns="http://schemas.microsoft.com/developer/msbuild/2003"\
>
"""
_msbuildFiltersTailer = """\
</Project>
"""

_msbuildFolder = """\
    <Filter Include="%(name)s">
      <UniqueIdentifier>%(guid)s</UniqueIdentifier>
    </Filter>
"""

_msbuildFile = """\
    <None Include="%(name)s">
      <Filter>%(filter)s</Filter>
    </None>
"""

_msbuildFileNoFilter = """\
    <None Include="%(name)s" />
"""

class MsBuildFiltersGenerator(object):
  """I am a class that is able to generate a single .vcproj file from
  its configuration information.
  """

  # Default member values
  encoding = 'utf-8'
  type = "Filters"

  def __init__(self, configuration, project):
    """Construct a new project generator instance.

    @param project: A Project object containing all info required for the project.
    """
    self.configuration = configuration
    self.project = project
    self.projectName = project.name
    self.projectDir = project.dir
    self.projectFiltersPath = project.filtersPath
    self.version = project.version
    self.configs = project.configurations.values()

  def build(self):
    """Create and write the .vcproj file.

    Throws an exception if building the project file fails.
    """
    _writeIt(self, self.projectFiltersPath)

  def _writeContents(self, writer):
    """Write the project to the currently open file.
    """
    self._writeFiltersHeader(writer)
    self._writeFoldersAndFiles(writer)
    self._writeFiltersTailer(writer)

  def _writeFiltersHeader(self, writer):
    """Write the project header section to the currently open file.

    This should be written at the start of the file.
    """
    writer.write(_msbuildFiltersHeader % {
      "encoding" : escapeAttr(self.encoding),
      "version" : escapeAttr(self.version),
      })

  def _writeFiltersTailer(self, writer):
    """Write the project tailer to the file.

    This should be the last content written to the file as it closes off
    datastructures written by the header.
    """
    writer.write(_msbuildFiltersTailer)

  def _writeFoldersAndFiles(self, writer):

    configItems = {}
    for config in self.configs:
      configItems[config] = convertToProjectItems(
        self.configuration,
        config.items,
        self.projectDir,
        )

    writer.write('  <ItemGroup>\n')
    self._writeSubFolders(writer, configItems)
    writer.write('  </ItemGroup>\n')

    writer.write('  <ItemGroup>\n')
    self._writeSubFiles(writer, configItems)
    writer.write('  </ItemGroup>\n')

  def _writeSubFolders(self, writer, configItems, parent=None):
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
      if parent:
        path = parent + "\\" + name
      else:
        path = name
      guid = generateGuid(path)

      writer.write(_msbuildFolder % {
        "name" : escapeAttr(path),
        "guid" : escapeAttr(guid),
        })

      # Recurse on each filter's subitems
      filterSubItems = mergedFilterSubItems[name]
      self._writeSubFolders(writer, filterSubItems, path)

  def _writeSubFiles(self, writer, configItems, parent=None):
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
      if parent:
        path = parent + "\\" + name
      else:
        path = name

      # Recurse on each filter's subitems
      filterSubItems = mergedFilterSubItems[name]
      self._writeSubFiles(writer, filterSubItems, path)

    # Write out all of the <File> subitems
    filePaths = mergedFileItemConfigs.keys()
    filePaths.sort()
    for path in filePaths:
      if parent:
        writer.write(_msbuildFile % {
          "name" : escapeAttr(path),
          "filter" : escapeAttr(parent),
          })
      else:
        writer.write(_msbuildFileNoFilter % {
          "name" : escapeAttr(path),
          })

class MsvsSolutionGenerator(object):
  """I am the class that does the actual writing of solution files.
  """

  # Default member values
  file = None
  encoding = 'utf-8'
  type = "Solution"

  def __init__(self, configuration, solution, registry):
    """Construct a new solution file writer.

    @param solution: The Solution object containing details of solution
    file to build.

    @param registry: The ProjectRegistry to use to find details of referenced
    projects.
    """
    self.configuration = configuration
    self.registry = registry
    self.solution = solution
    self.name = solution.name
    self.solutionDir = solution.dir
    self.solutionFilePath = solution.path
    self.version = solution.version
    self.isDotNet = solution.version in ['7.00', '8.00']

    self.solutionConfigurations = list(solution.configurations.values())
    self.solutionConfigurations.sort(key=lambda config: (config.name, config.platform))

    self.solutionGUID = generateGuid(self.solutionFilePath)

    # Construct a sorted list all project files
    projectFilePathToProject = {}
    for solutionConfig in self.solutionConfigurations:
      for projectConfig in solutionConfig.projectConfigurations:
        project = self.registry.getProjectByPath(projectConfig.path)
        if project is not None:
          key = (projectConfig.name, projectConfig.platform)
          projectConfig = project.configurations.get(key, None)
          if projectConfig is None:
            continue
          path = project.path
          projectFilePathToProject[path] = project
        else:
          print "Warning: skipping project %s (not built by cake)" % projectConfig.path
    projectFilePaths = projectFilePathToProject.keys()
    projectFilePaths.sort()
    self.projects = [projectFilePathToProject[p] for p in projectFilePaths]

    variants = set()
    for solutionConfig in self.solutionConfigurations:
      for projectConfig in solutionConfig.projectConfigurations:
        solutionVariant = self.getSolutionVariant(solutionConfig)
        projectVariant = self.getProjectVariant(projectConfig)

        variants.add((solutionVariant, projectVariant))
    self.variants = variants

  def getSolutionVariant(self, solutionConfig):
    if self.isDotNet:
      # .NET VS versions do not support user-defined solution platform names,
      # so use a project config name in an attempt to find a unique config name.
      if solutionConfig.projectConfigurations:
        return solutionConfig.projectConfigurations[0].name
      else:
        return solutionConfig.name
    else:
      return "%s|%s" % (solutionConfig.name, solutionConfig.platform)

  def getProjectVariant(self, projectConfig):
    return "%s|%s" % (projectConfig.name, projectConfig.platform)

  def getRelativePath(self, path):
    """Return path relative to the solution file.
    """
    abspath = self.configuration.abspath
    return cake.path.relativePath(abspath(path), abspath(self.solutionDir))

  def build(self):
    """Actually write the target file.
    """
    _writeIt(self, self.solutionFilePath)

  def _writeContents(self, writer):
    """Write the solution part (this is essentially the whole file's contents)
    """
    writer.write(u"\ufeff\r\n") # BOM
    self._writeHeader(writer)
    self._writeProjectsSection(writer)
    self._writeGlobalSection(writer)

  def _writeHeader(self, writer):
    """Write the solution header.

    Visual Studio uses this to determine which version of the .sln format this is.
    """
    writer.write(
      "Microsoft Visual Studio Solution File, Format Version %(version)s\r\n" % {
        'version' : self.version,
        }
      )
    writer.write(
      "# Generated by Cake for Visual Studio\r\n"
      )

  def _writeProjectsSection(self, writer):
    """Write the projects section.

    This section declares all of the constituent project files.
    """
    # Build a global list of all projects across all solution configurations
    for project in self.projects:
      self._writeProject(writer, project)

  def _writeProject(self, writer, project):
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

    writer.write('Project("%s") = "%s", "%s", "%s"\r\n' % (
      internalGuid, projectName, relativePath, externalGuid,
      ))

    if self.isDotNet:
      writer.write("\tProjectSection(ProjectDependencies) = postProject\r\n")
      writer.write("\tEndProjectSection\r\n")

    writer.write('EndProject\r\n')

  def _writeGlobalSection(self, writer):
    """Write all global sections.
    """
    writer.write("Global\r\n")
    self._writeSourceCodeControlSection(writer)
    self._writeSolutionConfigurationPlatformsSection(writer)
    self._writeProjectConfigurationPlatformsSection(writer)
    if self.isDotNet:
      self._writeExtensibilityGlobalsSection(writer)
      self._writeExtensibilityAddInsSection(writer)
    else:
      self._writeSolutionPropertiesSection(writer)
    writer.write("EndGlobal\r\n")

  def _writeSourceCodeControlSection(self, writer):
    """Write the section that defines the source code control for the projects.

    Looks up the MSVS_SCC_PROVIDER of the environment used to build the projects.
    """
    projectsWithScc = []

    for project in self.projects:
      if project.sccProvider is not None:
        projectsWithScc.append(project)

    if not projectsWithScc:
      return

    writer.write("\tGlobalSection(SourceCodeControl) = preSolution\r\n")

    writer.write(
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

      writer.write(
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

    writer.write(
      "\t\tSolutionUniqueID = %s\r\n" % self.solutionGUID
      )
    writer.write("\tEndGlobalSection\r\n")

  def _writeSolutionConfigurationPlatformsSection(self, writer):

    if not self.solutionConfigurations:
      return

    if self.isDotNet:
      writer.write(
        "\tGlobalSection(SolutionConfiguration) = preSolution\r\n"
        )
    else:
      writer.write(
        "\tGlobalSection(SolutionConfigurationPlatforms) = preSolution\r\n"
        )

    for solutionVariant, _ in self.variants:
      writer.write("\t\t%s = %s\r\n" % (
        solutionVariant,
        solutionVariant,
        ))

    writer.write("\tEndGlobalSection\r\n")

  def _writeProjectConfigurationPlatformsSection(self, writer):

    if self.isDotNet:
      writer.write("\tGlobalSection(ProjectConfiguration) = postSolution\r\n")
    else:
      writer.write("\tGlobalSection(ProjectConfigurationPlatforms) = postSolution\r\n")

    # Note: Not bothering to sort these because VS seems to have a strange sort
    # order ('0' comes after '9').
    for solutionConfig in self.solutionConfigurations:
      for projectConfig in solutionConfig.projectConfigurations:
        project = self.registry.getProjectByPath(projectConfig.path)
        if project is None:
          continue # Skip unknown projects

        guid = project.externalGuid
        solutionVariant = self.getSolutionVariant(solutionConfig)
        projectVariant = self.getProjectVariant(projectConfig)

        writer.write(
          "\t\t%(guid)s.%(slnvariant)s.ActiveCfg = %(projvariant)s\r\n" % {
            "guid" : guid,
            "slnvariant" : solutionVariant,
            "projvariant" : projectVariant,
            })

        if projectConfig.build:
          writer.write(
            "\t\t%(guid)s.%(slnvariant)s.Build.0 = %(projvariant)s\r\n" % {
              "guid" : guid,
              "slnvariant" : solutionVariant,
              "projvariant" : projectVariant,
              })

    writer.write("\tEndGlobalSection\r\n")

  def _writeExtensibilityGlobalsSection(self, writer):
    writer.write("\tGlobalSection(ExtensibilityGlobals) = postSolution\r\n")
    writer.write("\tEndGlobalSection\r\n")

  def _writeExtensibilityAddInsSection(self, writer):
    writer.write("\tGlobalSection(ExtensibilityAddIns) = postSolution\r\n")
    writer.write("\tEndGlobalSection\r\n")

  def _writeSolutionPropertiesSection(self, writer):
    writer.write("\tGlobalSection(SolutionProperties) = preSolution\r\n")
    writer.write("\t\tHideSolutionNode = FALSE\r\n")
    writer.write("\tEndGlobalSection\r\n")
