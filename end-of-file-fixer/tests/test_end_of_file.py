import os
import subprocess
import sys
import tempfile
import unittest

ACTION_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ACTION_DIR)

from end_of_file import fixed_content  # noqa: E402

SCRIPT = os.path.join(ACTION_DIR, "end_of_file.py")


class FixedContentTest(unittest.TestCase):
    def test_correct_endings_are_unchanged(self):
        for data in (b"", b"a\n", b"a\r\n", b"a\n\nb\n", b"a\r\nb\r\n"):
            self.assertEqual(fixed_content(data), data)

    def test_missing_newline_is_added(self):
        self.assertEqual(fixed_content(b"a"), b"a\n")

    def test_missing_newline_follows_crlf_files(self):
        self.assertEqual(fixed_content(b"a\r\nb"), b"a\r\nb\r\n")

    def test_extra_newlines_are_removed(self):
        self.assertEqual(fixed_content(b"a\n\n\n"), b"a\n")
        self.assertEqual(fixed_content(b"a\r\n\r\n"), b"a\r\n")

    def test_only_newlines_become_empty(self):
        self.assertEqual(fixed_content(b"\n\n"), b"")
        self.assertEqual(fixed_content(b"\r\n"), b"")


class ScriptTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name

    def write(self, name, data):
        path = os.path.join(self.directory, name)
        with open(path, "wb") as file:
            file.write(data)
        return name

    def read(self, name):
        with open(os.path.join(self.directory, name), "rb") as file:
            return file.read()

    def run_script(self, names, *args):
        return subprocess.run(
            [sys.executable, SCRIPT, *args],
            input="\n".join(names) + "\n",
            capture_output=True,
            text=True,
            cwd=self.directory,
        )

    def test_check_fails_without_changing_the_file(self):
        name = self.write("bad.txt", b"a")
        result = self.run_script([name])
        self.assertEqual(result.returncode, 1)
        self.assertIn("::error file=bad.txt,", result.stdout)
        self.assertEqual(self.read(name), b"a")

    def test_check_passes_on_correct_files(self):
        result = self.run_script([self.write("good.txt", b"a\n")])
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("::error", result.stdout)

    def test_fix_repairs_the_file_and_passes(self):
        name = self.write("bad.txt", b"a\n\n")
        result = self.run_script([name], "--fix")
        self.assertEqual(result.returncode, 0)
        self.assertIn("::warning file=bad.txt,", result.stdout)
        self.assertEqual(self.read(name), b"a\n")

    def test_binary_files_are_skipped(self):
        name = self.write("image.bin", b"\0a")
        result = self.run_script([name], "--fix")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.read(name), b"\0a")

    def test_symlinks_and_missing_paths_are_skipped(self):
        target = self.write("target.txt", b"a")
        os.symlink(target, os.path.join(self.directory, "link.txt"))
        result = self.run_script(["link.txt", "missing.txt", ""], "--fix")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.read(target), b"a")

    def test_excluded_paths_are_skipped(self):
        excluded = self.write("generated.txt", b"a")
        checked = self.write("source.txt", b"a")
        result = self.run_script([excluded, checked], "--fix", "--exclude=^generated")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.read(excluded), b"a")
        self.assertEqual(self.read(checked), b"a\n")

    def test_invalid_exclude_pattern_fails(self):
        name = self.write("bad.txt", b"a")
        result = self.run_script([name], "--fix", "--exclude=(")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid exclude pattern", result.stdout)
        self.assertEqual(self.read(name), b"a")

    def test_paths_are_escaped_in_annotations(self):
        result = self.run_script([self.write("a,b%c.txt", b"a")])
        self.assertIn("file=a%2Cb%25c.txt,", result.stdout)


if __name__ == "__main__":
    unittest.main()
