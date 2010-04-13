from cake.tools import script, env, zipping

def shouldInclude(s):
  return True

def shouldExclude(s):
  return s.find("exclude") != -1

zipping.extract(
  env.expand("${BUILD}/unzip"),
  script.cwd("unzip.zip"),
  onlyNewer=True,
  removeStale=True,
  includeMatch=shouldInclude,
  excludeMatch=shouldExclude,
  )
