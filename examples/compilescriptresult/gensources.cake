import cake.filesys
import cake.path
from cake.tools import env, script, logging

def makeFile(target, contents):
  engine = script.engine
  configuration = script.configuration
  def run():
    absTarget = configuration.abspath(target)
    logging.outputInfo("Creating %s\n" % target)
    cake.filesys.makeDirs(cake.path.dirName(absTarget))
    with open(absTarget, 'wb') as f:
      f.write(contents)
  return script.run(run, targets=[target], args=[contents])[0]

sources = []

sources.append(makeFile(
  target=env.expand('${BUILD}/compilescriptresult/a.c'),
  contents="""
void a()
{
}
  """))
sources.append(makeFile(
  target=env.expand('${BUILD}/compilescriptresult/b.c'),
  contents="""
void b()
{
}
  """))

mainSource = makeFile(
  target=env.expand('${BUILD}/compilescriptresult/main.c'),
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

script.setResult(
  sources=sources,
  main=mainSource,
  )
