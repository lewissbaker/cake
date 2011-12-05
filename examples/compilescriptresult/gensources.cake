#-------------------------------------------------------------------------------
# Script used to generate the source files.
#-------------------------------------------------------------------------------
import cake.filesys
import cake.path
from cake.tools import script, logging

def makeFile(target, contents):
  engine = script.engine
  configuration = script.configuration
  def run():
    absTarget = configuration.abspath(configuration.basePath(target))
    logging.outputInfo("Creating %s\n" % target)
    cake.filesys.makeDirs(cake.path.dirName(absTarget))
    f = open(absTarget, 'wb')
    try:
      f.write(contents.encode('latin1'))
    finally:
      f.close()
  return script.run(run, targets=[target], args=[contents])[0]

sources = []

sources.append(makeFile(
  target='../build/$VARIANT/compilescriptresult/a.c',
  contents="""
void a()
{
}
  """))
sources.append(makeFile(
  target='../build/$VARIANT/compilescriptresult/b.c',
  contents="""
void b()
{
}
  """))

mainSource = makeFile(
  target='../build/$VARIANT/compilescriptresult/main.c',
  contents="""
extern void a();
extern void b();

int main()
{
  a();
  b();
  return 0;  
}
""")

# Set the 'sources' result of this script to the list of sources and 'main'
# to the main source file.
script.setResult(
  sources=sources,
  main=mainSource,
  )
