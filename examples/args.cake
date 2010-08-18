# Options will be stored in 'engine.options' which you can later access
# in your own config.cake.
from cake.engine import Script

script = Script.getCurrent()
engine = script.engine
parser = engine.parser

parser.add_option(
  "-p", "--projects",
  action="store_true",
  dest="createProjects",
  help="Create projects instead of building a variant.",
  default=False,
  )
