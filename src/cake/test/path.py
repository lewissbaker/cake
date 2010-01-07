import unittest
import os.path

class PathTests(unittest.TestCase):
  
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
