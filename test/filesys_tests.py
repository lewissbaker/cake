import os
from cake.test.framework import caketest

@caketest(fixture="copyfile")
def testCopyWhenNotExist(t):
  output = t.runCake("copyifnewer.cake")
  output.checkSucceeded()
  output.checkHasLine("Copying readme.txt to doc.txt")

  t.checkFilesAreSame("readme.txt", "doc.txt")

@caketest(fixture="copyfile")
def testNoCopyWhenUpToDate(t):
  t.runCake("copyifnewer.cake").checkSucceeded()
  
  # Should be a no-op when run a second time
  t.runCake("copyifnewer.cake").checkBuildWasNoop()

@caketest(fixture="copyfile")
def testCopyWhenSourceHasChanged(t):
  t.runCake("copyifnewer.cake").checkSucceeded()

  t.writeTextFile("readme.txt", "some other content")

  output = t.runCake("copyifnewer.cake")
  output.checkSucceeded()
  output.checkHasLine("Copying readme.txt to doc.txt")

@caketest(fixture="copyfile")
def testCopyWhenTargetIsRemoved(t):
  t.runCake("copyifnewer.cake").checkSucceeded()

  t.removeFile("doc.txt")

  output = t.runCake("copyifnewer.cake")
  output.checkSucceeded()
  output.checkHasLine("Copying readme.txt to doc.txt")

@caketest(fixture="copyfile")
def testCopyFailsIfTargetIsMissing(t):
  t.removeFile("readme.txt")
  output = t.runCake("copyifnewer.cake")
  output.checkFailed()
  output.checkHasLineMatching(
    r"doc\.txt:.*No such file or directory.*readme\.txt.*")

@caketest(fixture="copyfile")
def testCopyAlwaysIfUpToDate(t):
  output = t.runCake("copyalways.cake")
  output.checkSucceeded()
  output.checkHasLine("Copying readme.txt to doc.txt")
  
  t.checkFilesAreSame("readme.txt", "doc.txt")

  # Still copies file 
  output = t.runCake("copyalways.cake")
  output.checkSucceeded()
  output.checkHasLine("Copying readme.txt to doc.txt")

  t.checkFilesAreSame("readme.txt", "doc.txt")
