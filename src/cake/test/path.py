"""Path Unit Tests.
"""

import unittest
import os.path
import os
import sys
import platform

class PathTests(unittest.TestCase):

  def testAbsPath(self):
    from cake.path import absPath
    # Just test it runs
    self.assertEqual(absPath(__file__), os.path.abspath(__file__))
    
  def testAddPrefix(self):
    from cake.path import addPrefix
    self.assertEqual(addPrefix(".dat", "lib"), "lib.dat")
    self.assertEqual(addPrefix("file", "lib"), "libfile")
    self.assertEqual(addPrefix("file.dat", "lib"), "libfile.dat")
    self.assertEqual(addPrefix("/file.dat", "lib"), "/libfile.dat")
    self.assertEqual(addPrefix("/path/to/file", "lib"), "/path/to/libfile")
    self.assertEqual(addPrefix("/path/to/file.dat", "lib"), "/path/to/libfile.dat")

  def testBaseName(self):
    from cake.path import baseName
    self.assertEqual(baseName(".dat"), ".dat")
    self.assertEqual(baseName("file"), "file")
    self.assertEqual(baseName("file.dat"), "file.dat")
    self.assertEqual(baseName("/path/to/file"), "file")
    self.assertEqual(baseName("/path/to/file.dat"), "file.dat")
  
  def testBaseNameWithoutExtension(self):
    from cake.path import baseNameWithoutExtension
    self.assertEqual(baseNameWithoutExtension(".dat"), "")
    self.assertEqual(baseNameWithoutExtension("file"), "file")
    self.assertEqual(baseNameWithoutExtension("file.dat"), "file")
    self.assertEqual(baseNameWithoutExtension("/path/to/file"), "file")
    self.assertEqual(baseNameWithoutExtension("/path/to/file.dat"), "file")

  def testCommonPath(self):
    from cake.path import commonPath
    self.assertEqual(commonPath("", ""), "")
    self.assertEqual(commonPath(".", ".."), "")
    self.assertEqual(commonPath("/.", "/.."), "")
    self.assertEqual(commonPath("/./", "/./.."), "/.")
    self.assertEqual(commonPath("/..", "/../"), "/..")
    self.assertEqual(commonPath("./", "./"), ".")
    self.assertEqual(commonPath("a", "a"), "a")
    self.assertEqual(commonPath("a", "ab"), "")
    self.assertEqual(commonPath("a/b", "a/c"), "a")
    self.assertEqual(commonPath("ab/c", "a"), "")
    self.assertEqual(commonPath("ab/c", "ab"), "ab")
    self.assertEqual(commonPath("a/b/c", "a/b/d"), "a/b")
    self.assertEqual(commonPath("a/b/cd", "a/b/c"), "a/b")
    self.assertEqual(commonPath("a/bc/d", "a/bcd/e"), "a")
    self.assertEqual(commonPath("a/b/c", "a/b/c/d"), "a/b/c")
  
  def testDirName(self):
    from cake.path import dirName
    self.assertEqual(dirName(".dat"), "")
    self.assertEqual(dirName("file"), "")
    self.assertEqual(dirName("file.dat"), "")
    self.assertEqual(dirName("/path/to/file"), "/path/to")
    self.assertEqual(dirName("/path/to/file.dat"), "/path/to")
  
  def testExists(self):
    from cake.path import exists
    # Just test it runs
    self.assertEqual(exists(__file__), os.path.exists(__file__))
  
  def testExpandVars(self):
    from cake.path import expandVars
    self.assertEqual(expandVars("", {}), "")
    self.assertEqual(expandVars("foo", {}), "foo")
    self.assertEqual(expandVars("$", {}), "{MISSING_SYMBOL_}")
    self.assertEqual(expandVars("$$", {}), "$")
    self.assertEqual(expandVars("${}", {}), "{MISSING_SYMBOL_}")
    self.assertEqual(expandVars("$var", {}), "{MISSING_SYMBOL_var}")
    self.assertEqual(
      expandVars("$var/$foo", {}),
      "{MISSING_SYMBOL_var}/{MISSING_SYMBOL_foo}"
      )
    self.assertEqual(expandVars("${var}", {}), "{MISSING_SYMBOL_var}")
    self.assertEqual(expandVars("${var}", {"var": "x"}), "x")
    self.assertEqual(expandVars("${var}", {"var": "$x/$x", "x": "foo"}), "foo/foo")

  def testExtension(self):
    from cake.path import extension
    self.assertEqual(extension(""), "")
    self.assertEqual(extension("."), "")
    self.assertEqual(extension(".."), "")
    self.assertEqual(extension("/."), "")
    self.assertEqual(extension("/.."), "")
    self.assertEqual(extension("foo/."), "")
    self.assertEqual(extension("foo/.."), "")
    self.assertEqual(extension("./"), "")
    self.assertEqual(extension(".foo"), "")
    self.assertEqual(extension(".foo."), ".")
    self.assertEqual(extension(".foo.bar"), ".bar")
    self.assertEqual(extension("foo/.bar"), "")
    self.assertEqual(extension("foo.bar"), ".bar")
    self.assertEqual(extension("foo.bar.baz"), ".baz")
    self.assertEqual(extension("foo/baz"), "")
    self.assertEqual(extension("foo.bar/baz"), "")
    self.assertEqual(extension("foo.bar/baz.blah"), ".blah")

  def testFileSystemPath(self):
    # Tests are only valid on case-insensitive platforms
    if os.path.normcase('aBcD') == 'aBcD':
      return
    
    from cake.path import fileSystemPath
    self.assertEqual(fileSystemPath(""), "")
    self.assertEqual(fileSystemPath("."), ".")
    
    fileName = "aBcD.tXt"
    f = open(fileName, "wt")
    f.close()
    try:
      self.assertEqual(fileSystemPath("abcd.txt"), fileName)
      self.assertEqual(fileSystemPath("./abcd.txt"), "./" + fileName)
    finally:
      os.remove(fileName)
    
    dirName = "WhaT" 
    os.mkdir(dirName)
    try:
      path = dirName + "/" + fileName
      f = open(path, "wt")
      f.close()
      try:
        self.assertEqual(fileSystemPath("whAT/aBCd.txt"), path)
        self.assertEqual(fileSystemPath("./whAT/aBCd.txt"), "./" + path)
        self.assertEqual(fileSystemPath("whAT/.."), dirName + "/..")
        self.assertEqual(fileSystemPath("whAT/../WHat"), dirName + "/../" + dirName)
        self.assertEqual(
          fileSystemPath("./whAT/../WHAT/./aBCd.txt"),
          "./" + dirName + "/../" + dirName + "/./" + fileName,
          )
      finally:
        os.remove(path)
    finally:
      os.rmdir(dirName)

  def testHasExtension(self):
    from cake.path import hasExtension
    self.assertFalse(hasExtension(""))
    self.assertFalse(hasExtension("."))
    self.assertFalse(hasExtension("/."))
    self.assertFalse(hasExtension("/.."))
    self.assertFalse(hasExtension(".."))
    self.assertFalse(hasExtension("..foo"))
    self.assertFalse(hasExtension(".hidden"))
    self.assertTrue(hasExtension(".hidden.foo"))
    self.assertFalse(hasExtension("dir/.hidden"))
    self.assertTrue(hasExtension("foo.txt"))
    self.assertTrue(hasExtension("foo."))
    self.assertTrue(hasExtension("foo.c"))
    self.assertTrue(hasExtension("foo.bar.baz"))
    self.assertTrue(hasExtension("/foo.bar"))
    self.assertTrue(hasExtension("baz/foo.bar"))
    self.assertTrue(hasExtension("baz.blah/foo.bar"))
    self.assertFalse(hasExtension("foo"))
    self.assertFalse(hasExtension("foo.bar/"))
    self.assertFalse(hasExtension("foo.bar/foo"))
    self.assertFalse(hasExtension("foo/baz.bar\\blah"))
    self.assertFalse(hasExtension("foo\\baz.bar/blah"))
    self.assertTrue(hasExtension("foo/baz\\blah.bar"))
    self.assertTrue(hasExtension("foo\\baz/blah.bar"))
  
  def testIsAbs(self):
    from cake.path import isAbs
    # Just test it runs
    self.assertEqual(isAbs(__file__), os.path.isabs(__file__))

  def testIsDir(self):
    from cake.path import isDir
    # Just test it runs
    self.assertEqual(isDir(__file__), os.path.isdir(__file__))

  def testIsFile(self):
    from cake.path import isFile
    # Just test it runs
    self.assertEqual(isFile(__file__), os.path.isfile(__file__))
 
  def testIsMount(self):
    from cake.path import isMount
    # Just test it runs
    self.assertEqual(isMount(__file__), os.path.ismount(__file__))
         
  def testJoin(self):
    from cake.path import join
    self.assertEqual(join(), "")
    self.assertEqual(join("a"), "a")
    self.assertEqual(join("a", "b"), os.path.join("a", "b"))
    self.assertEqual(join(["a"]), ["a"])
    self.assertEqual(join(["a", "b"]), ["a", "b"])
    self.assertEqual(join("a", ["b"]), [os.path.join("a", "b")])
    self.assertEqual(join("a", ["b", "c"]), [
      os.path.join("a", "b"),
      os.path.join("a", "c"),
      ])
    self.assertEqual(join("a", ["b", "c"], "d"), [
      os.path.join("a", "b", "d"),
      os.path.join("a", "c", "d"),
      ])
    self.assertEqual(join(["a", "b"], ["c", "d"]), [
      os.path.join("a", "c"),
      os.path.join("a", "d"),
      os.path.join("b", "c"),
      os.path.join("b", "d"),
      ])

  def testRelativePath(self):
    from cake.system import isWindows
    from cake.path import relativePath
    
    self.assertEqual(relativePath("", ""), ".")
    self.assertEqual(relativePath("a", "a"), ".")
    self.assertEqual(relativePath("a", "ab"), ".." + os.path.sep + "a")
    self.assertEqual(relativePath("a/b", "a/c"), ".." + os.path.sep + "b")
    self.assertEqual(relativePath("ab/c", "a"), ".." + os.path.sep + "ab"  + os.path.sep + "c")
    self.assertEqual(relativePath("ab/c", "ab"), "c")
    self.assertEqual(relativePath("a/b/c", "a/b"), "c")
    self.assertEqual(relativePath("a/b/c", "a/b/"), "c")
    self.assertEqual(relativePath("a/b/c", "a/b/d"), ".." + os.path.sep + "c")
    self.assertEqual(relativePath("a/b/cd", "a/b/c"), ".." + os.path.sep + "cd")
    self.assertEqual(
      relativePath("a/bc/d", "a/bcd/e"),
      ".." + os.path.sep + ".." + os.path.sep + "bc" + os.path.sep + "d",
      )
    self.assertEqual(relativePath("a/b/c", "a/b/c/d"), "..")
    self.assertEqual(relativePath("a/b/c/d", "a/b"), "c" + os.path.sep + "d")
    self.assertEqual(relativePath("a/b/c/d", "a/b/"), "c" + os.path.sep + "d")
    
    if isWindows():
      self.assertEqual(relativePath("c:", "d:"), "c:")
      self.assertEqual(relativePath("c:\\", "d:\\"), "c:\\")
      self.assertEqual(relativePath("c:\\ab", "d:\\dc"), "c:\\ab")
      self.assertEqual(relativePath("c:\\ab", "c:\\dc"), "..\\ab")
      self.assertEqual(relativePath("\\\\unc1", "\\\\unc2"), "\\\\unc1")

if __name__ == "__main__":
  suite = unittest.TestLoader().loadTestsFromTestCase(PathTests)
  runner = unittest.TextTestRunner(verbosity=2)
  sys.exit(not runner.run(suite).wasSuccessful())
