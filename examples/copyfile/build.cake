from cake.tools import env, filesys, script

filesys.copyFile(
  source=script.cwd("copyme.txt"),
  target=env.expand("${BUILD}/copyfile/copyme.txt"),
  )
