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
    "--output=html/",
    "--no-private",
    "--exclude=cake.test",
    "src/cake",
    ]
  epydoc.cli.cli()
  sys.exit(0)
