from cake.tools import filesys, script

filesys.copyFile(
    source=script.cwd("readme.txt"),
    target=script.cwd("doc.txt"),
    onlyNewer=False,
    )
