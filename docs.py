"""Document generation.

This script is used to generate documentation for Cake.

@see: Cake Build System (http://sourceforge.net/projects/cake-build)
@copyright: Copyright (c) 2010 Lewis Baker, Stuart McMahon.
@license: Licensed under the MIT license (see license.txt).
"""

if __name__ == "__main__":
  import sys
  import epydoc.cli
  sys.argv += [
    "--verbose",
    "--name=Cake Build System",
    "--url=http://cake-build.sf.net/",
    "--inheritance=listed",
    "--css=white",
    "--html",
    "--output=docs/",
    "--no-private",
    "--exclude=cake.test",
    "src/cake",
    ]
  epydoc.cli.cli()
  sys.exit(0)
