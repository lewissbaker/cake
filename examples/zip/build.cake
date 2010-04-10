from cake.tools import script, env, zipping

def shouldInclude(s):
  return True

def shouldExclude(s):
  return s.find("exclude") != -1
  
zipping.compress(
  env.expand("${BUILD}/zip/zip.zip"),
  script.cwd("zipme"),
  onlyNewer=True,
  removeStale=True,
  includeMatch=shouldInclude,
  excludeMatch=shouldExclude,
  )
