import cake.system
from cake.test.framework import caketest

@caketest(fixture="c_library")
def testBuildCLibrary(t):
  out = t.runCake()
  out.checkSucceeded()
  out.checkHasLine("Compiling foo.c")
  out.checkHasLineMatching("Archiving foo\\.(a|lib)")

  t.runCake().checkBuildWasNoop()

@caketest(fixture="c_library")
def testModifyAndRebuildCLibrary(t):
  t.runCake().checkSucceeded()

  t.touchFile("foo.h")

  out = t.runCake()
  out.checkSucceeded()
  out.checkHasLine("Compiling foo.c")
  out.checkHasLineMatching("Archiving foo\\.(a|lib)")

@caketest(fixture="uselibrary")
def testCompileProgramUsingLibrary(t):
  out = t.runCake("main")
  out.checkSucceeded()
  out.checkHasLine("Compiling main/main.cpp")
  out.checkHasLine("Compiling printer/source/printer.cpp")
  out.checkHasLine("Archiving printer/lib/printer.lib")

  t.runCake("main").checkBuildWasNoop()
  t.runCake("printer").checkBuildWasNoop()
