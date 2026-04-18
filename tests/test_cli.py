import io
import unittest

from client.cli import DFSShell


class DFSShellTests(unittest.TestCase):
    def setUp(self):
        self.shell = DFSShell()
        self.output = io.StringIO()
        self.shell.stdout = self.output

    def test_file_workflow_and_sort_output(self):
        self.shell.onecmd("touch example.txt")
        self.shell.onecmd("append example.txt tests/sample_input.txt")
        self.shell.onecmd("ls")
        self.shell.onecmd("sort_file example.txt sorted.txt")

        sorted_content = self.shell.dfs.read("sorted.txt").decode("utf-8")
        keys = [line.split(",", 1)[0] for line in sorted_content.splitlines()]
        self.assertIn("example.txt", self.output.getvalue())
        self.assertEqual(keys, sorted(keys))
        self.assertIn("example.txt", self.shell.dfs.ls())
        self.assertEqual(len(self.shell.topology.chord_nodes), 5)
        self.assertEqual(len(self.shell.topology.paxos_replicas), 3)

    def test_missing_append_path_reports_error(self):
        self.shell.onecmd("append example.txt missing-file.txt")

        self.assertIn("Local file not found", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
