import unittest
from pathlib import Path

from chord.node import create_local_chord_ring
from dfs.metadata import Metadata
from dfs.topology import create_local_dfs_topology
from replication.paxos import create_local_paxos_cluster


class ChordRoutingTests(unittest.TestCase):
    def test_put_get_delete_route_to_successor_node(self):
        nodes = create_local_chord_ring(num_nodes=5)
        entry = nodes[0]
        key = Metadata("routed.txt").get_metadata_key()
        owner = entry.locate_successor(key)

        entry.put(key, "metadata")

        self.assertEqual(len(nodes), 5)
        self.assertIn(key, owner._store)
        self.assertEqual(entry.get(key), "metadata")
        self.assertTrue(entry.delete(key))
        self.assertIsNone(entry.get(key))


class PaxosTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path("storage/test_paxos_log.txt")
        if self.log_path.exists():
            self.log_path.unlink()

    def tearDown(self):
        if self.log_path.exists():
            self.log_path.unlink()

    def test_majority_commit_and_ordered_replica_logs(self):
        applied = []
        replicas = create_local_paxos_cluster(log_path=str(self.log_path))
        replicas[0].set_apply_callback(applied.append)

        first = {"op": "touch", "filename": "a.txt"}
        second = {"op": "delete_file", "filename": "a.txt", "pages": []}

        self.assertTrue(replicas[0].propose(first))
        self.assertTrue(replicas[0].propose(second))

        self.assertEqual(replicas[0].proposal_number, 2)
        self.assertEqual(applied, [first, second])
        for replica in replicas:
            self.assertEqual(
                [entry["operation"] for entry in replica.log],
                [first, second],
            )

        log_text = self.log_path.read_text()
        self.assertIn("ACCEPT", log_text)
        self.assertIn("LEARN", log_text)
        self.assertIn("COMMIT", log_text)


class DFSArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path("storage/test_dfs_paxos_log.txt")
        if self.log_path.exists():
            self.log_path.unlink()

    def tearDown(self):
        if self.log_path.exists():
            self.log_path.unlink()

    def test_dfs_mutations_use_paxos_and_chord_storage(self):
        topology = create_local_dfs_topology(log_path=str(self.log_path))
        dfs = topology.dfs

        self.assertTrue(dfs.touch("example.txt"))
        self.assertTrue(dfs.append("example.txt", "tests/sample_input.txt"))

        stat = dfs.stat("example.txt")
        self.assertEqual(stat["filename"], "example.txt")
        self.assertEqual(stat["num_pages"], 1)
        self.assertIn("replicas", stat["pages"][0])
        self.assertIn("owner", stat["pages"][0])
        self.assertEqual(dfs.read("example.txt"), Path("tests/sample_input.txt").read_bytes())

        page_guid = stat["pages"][0]["guid"]
        owner = topology.chord_nodes[0].locate_successor(page_guid)
        self.assertIn(page_guid, owner._store)

        log_text = self.log_path.read_text()
        self.assertIn("ACCEPT", log_text)
        self.assertIn("LEARN", log_text)
        self.assertIn("COMMIT", log_text)


if __name__ == "__main__":
    unittest.main()
