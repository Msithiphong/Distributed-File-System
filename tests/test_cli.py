import io
import unittest
from pathlib import Path

from client.cli import DFSShell
from dfs.topology import create_local_dfs_topology


class DFSShellTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path("storage/test_cli_paxos_log.txt")
        if self.log_path.exists():
            self.log_path.unlink()

        self.topology = create_local_dfs_topology(log_path=str(self.log_path))
        self.shell = DFSShell(dfs=self.topology.dfs)
        self.shell.topology = self.topology
        self.output = io.StringIO()
        self.shell.stdout = self.output

    def tearDown(self):
        if self.log_path.exists():
            self.log_path.unlink()

    def _clear_output(self):
        self.output.seek(0)
        self.output.truncate(0)

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

    def test_topology_paxos_log_and_failure_demo_commands(self):
        self.shell.onecmd("touch evidence.txt")

        self._clear_output()
        self.shell.onecmd("topology")
        topology_output = self.output.getvalue()
        self.assertIn("Chord node", topology_output)
        self.assertIn("fingers=[", topology_output)
        self.assertIn("Paxos leader:", topology_output)

        self._clear_output()
        self.shell.onecmd("paxos_log 20")
        paxos_output = self.output.getvalue()
        self.assertIn("ACCEPT", paxos_output)
        self.assertIn("LEARN", paxos_output)
        self.assertIn("COMMIT", paxos_output)

        self._clear_output()
        self.shell.onecmd("failure_demo")
        failure_output = self.output.getvalue()
        self.assertIn("Crashed follower replica", failure_output)
        self.assertIn("Majority commit succeeded", failure_output)
        self.assertIn("Recovered follower replica", failure_output)

    def test_sorts_the_large_sample_from_cli(self):
        self.shell.onecmd("append records.txt tests/sample_100_records.txt")
        self.shell.onecmd("sort_file records.txt records_sorted.txt")

        sorted_content = self.shell.dfs.read("records_sorted.txt").decode("utf-8")
        keys = [line.split(",", 1)[0] for line in sorted_content.splitlines()]

        self.assertGreaterEqual(len(keys), 100)
        self.assertEqual(keys, sorted(keys))

    def test_missing_append_path_reports_error(self):
        self.shell.onecmd("append example.txt missing-file.txt")

        self.assertIn("Local file not found", self.output.getvalue())


if __name__ == "__main__":
    unittest.main()
