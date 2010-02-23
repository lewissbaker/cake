from cake.tools import env, filesys

filesys.copyFile(
  source=filesys.cwd("copyme.txt"),
  target=env.expand("${BUILD}/copyfile/copyme.txt"),
  )
