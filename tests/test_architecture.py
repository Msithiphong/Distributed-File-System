import unittest
from pathlib import Path

from chord.node import create_local_chord_ring
from dfs.metadata import Metadata
from dfs.topology import create_local_dfs_topology
from replication.paxos import create_local_paxos_cluster


class ChordReplicationTests(unittest.TestCase):
    def test_replicated_put_get_and_delete_use_three_successors(self):
        nodes = create_local_chord_ring(num_nodes=5)
        entry = nodes[0]
        key = Metadata("replicated.txt").get_metadata_key()

        replica_nodes = entry.put_replicated(key, "metadata", count=3)
        stored_nodes = [node for node in nodes if key in node._store]

        self.assertEqual(len(replica_nodes), 3)
        self.assertEqual(
            [node.node_id for node in stored_nodes],
            [node.node_id for node in replica_nodes],
        )
        self.assertEqual(entry.get_replicated(key, count=3), "metadata")

        del replica_nodes[0]._store[key]
        self.assertEqual(entry.get_replicated(key, count=3), "metadata")

        self.assertTrue(entry.delete_replicated(key, count=3))
        self.assertTrue(all(key not in node._store for node in nodes))


class PaxosTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path("storage/test_paxos_log.txt")
        if self.log_path.exists():
            self.log_path.unlink()

    def tearDown(self):
        if self.log_path.exists():
            self.log_path.unlink()

    def test_all_active_replicas_apply_commits_in_proposal_order(self):
        applied = {}
        replicas = create_local_paxos_cluster(log_path=str(self.log_path))
        for replica in replicas:
            applied[replica.replica_id] = []
            replica.set_apply_callback(
                lambda operation, replica_id=replica.replica_id: applied[
                    replica_id
                ].append(operation)
            )

        first = {"op": "touch", "filename": "a.txt"}
        second = {"op": "delete_file", "filename": "a.txt", "pages": []}

        self.assertTrue(replicas[0].propose(first))
        self.assertTrue(replicas[0].propose(second))

        for replica in replicas:
            self.assertEqual(applied[replica.replica_id], [first, second])
            self.assertEqual(
                [entry["operation"] for entry in replica.log],
                [first, second],
            )

        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("ACCEPT", log_text)
        self.assertIn("LEARN", log_text)
        self.assertIn("COMMIT", log_text)

    def test_crashed_follower_still_allows_majority_commit_and_catch_up(self):
        applied = {}
        replicas = create_local_paxos_cluster(log_path=str(self.log_path))
        for replica in replicas:
            applied[replica.replica_id] = []
            replica.set_apply_callback(
                lambda operation, replica_id=replica.replica_id: applied[
                    replica_id
                ].append(operation)
            )

        follower = replicas[1]
        operation = {"op": "touch", "filename": "failure.txt"}

        follower.crash()
        self.assertTrue(replicas[0].propose(operation))
        self.assertEqual(applied[follower.replica_id], [])
        self.assertEqual(follower.log, [])

        follower.recover()
        replayed = follower.catch_up_from_leader()

        self.assertEqual(replayed, 1)
        self.assertEqual(applied[follower.replica_id], [operation])
        self.assertEqual(
            [entry["operation"] for entry in follower.log],
            [operation],
        )

        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("CRASH", log_text)
        self.assertIn("RECOVER", log_text)
        self.assertIn("CATCH_UP", log_text)
        self.assertIn("REPLAY", log_text)
        self.assertIn("SKIP ACCEPT inactive", log_text)
        self.assertIn("SKIP COMMIT inactive", log_text)
        self.assertIn("COMMIT", log_text)


class DFSArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path("storage/test_dfs_paxos_log.txt")
        if self.log_path.exists():
            self.log_path.unlink()

    def tearDown(self):
        if self.log_path.exists():
            self.log_path.unlink()

    def test_touch_append_stat_read_and_delete_use_replicated_storage(self):
        topology = create_local_dfs_topology(log_path=str(self.log_path))
        dfs = topology.dfs

        self.assertTrue(dfs.touch("example.txt"))
        self.assertTrue(dfs.append("example.txt", "tests/sample_input.txt"))

        stat = dfs.stat("example.txt")
        self.assertEqual(stat["filename"], "example.txt")
        self.assertEqual(stat["num_pages"], 1)
        self.assertEqual(len(stat["metadata_replicas"]), 3)
        self.assertEqual(len(stat["pages"][0]["replicas"]), 3)

        meta_key = Metadata("example.txt").get_metadata_key()
        page_guid = stat["pages"][0]["guid"]
        metadata_stores = [
            node for node in topology.chord_nodes if meta_key in node._store
        ]
        page_stores = [
            node for node in topology.chord_nodes if page_guid in node._store
        ]

        self.assertEqual(len(metadata_stores), 3)
        self.assertEqual(len(page_stores), 3)

        owner = topology.chord_nodes[0].locate_successor(page_guid)
        del owner._store[page_guid]
        self.assertEqual(
            dfs.read("example.txt"),
            Path("tests/sample_input.txt").read_bytes(),
        )

        self.assertTrue(dfs.delete_file("example.txt"))
        self.assertIsNone(dfs.stat("example.txt"))
        self.assertTrue(all(meta_key not in node._store for node in topology.chord_nodes))
        self.assertTrue(all(page_guid not in node._store for node in topology.chord_nodes))
        self.assertTrue(
            all("file_index" not in node._store for node in topology.chord_nodes)
        )

    def test_recovered_follower_replay_does_not_duplicate_pages(self):
        topology = create_local_dfs_topology(log_path=str(self.log_path))
        dfs = topology.dfs
        follower = topology.paxos_replicas[1]

        follower.crash()
        self.assertTrue(dfs.append("replay.txt", "tests/sample_input.txt"))
        follower.recover()
        replayed = follower.catch_up_from_leader()

        stat = dfs.stat("replay.txt")
        self.assertEqual(replayed, 1)
        self.assertEqual(stat["num_pages"], 1)
        self.assertEqual(len(stat["pages"]), 1)
        self.assertEqual(
            dfs.read("replay.txt"),
            Path("tests/sample_input.txt").read_bytes(),
        )

    def test_sorts_more_than_one_hundred_records_globally(self):
        topology = create_local_dfs_topology(log_path=str(self.log_path))
        dfs = topology.dfs

        self.assertTrue(dfs.append("records.txt", "tests/sample_100_records.txt"))
        self.assertTrue(dfs.sort_file("records.txt", "records_sorted.txt"))

        sorted_content = dfs.read("records_sorted.txt").decode("utf-8")
        keys = [line.split(",", 1)[0] for line in sorted_content.splitlines()]

        self.assertGreaterEqual(len(keys), 100)
        self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":
    unittest.main()
