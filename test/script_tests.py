import cake.system
from cake.test.framework import caketest

@caketest(fixture="scriptinclude")
def testScriptIncludeMissingTraceback(t):
  out = t.runCake()
  out.checkFailed()
  out.checkHasLineMatching("Failed to include cake script missing\\.cake:")
  out.checkHasLinesInOrder([
    "  from include2.cake",
    "  from include1.cake",
    "  from build.cake",
    ])
