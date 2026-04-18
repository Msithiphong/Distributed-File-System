"""
Simplified in-process Paxos protocol for DFS replication.
"""
from pathlib import Path
import threading


class PaxosReplica:
    def __init__(self, replica_id, peers=None, log_path="storage/paxos_log.txt"):
        self.replica_id = replica_id
        self.peers = peers or []
        self.leader = None
        self.proposal_number = 0
        self.accepted_number = 0
        self.accepted_value = None
        self.log = []
        self.log_path = Path(log_path)
        self.apply_callback = None
        self.lock = threading.Lock()

    def configure_cluster(self, replicas, leader_id=1):
        self.peers = replicas
        self.leader = leader_id

    def set_apply_callback(self, callback):
        self.apply_callback = callback

    def propose(self, operation):
        """Propose an operation as leader and commit after a majority learns it."""
        if not self.is_leader():
            leader = self._leader_replica()
            return leader.propose(operation)

        with self.lock:
            self.proposal_number += 1
            proposal_number = self.proposal_number

        self._write_log(
            f"Node {self.replica_id}: PROPOSE {self._describe(operation)}, "
            f"proposal #{proposal_number}"
        )

        accepts = []
        for replica in self.peers:
            if replica.receive_accept(proposal_number, operation, self.replica_id):
                accepts.append(replica)

        majority = (len(self.peers) // 2) + 1
        if len(accepts) < majority:
            self._write_log(
                f"Node {self.replica_id}: ABORT {self._describe(operation)}, "
                f"proposal #{proposal_number}, learns 0/{majority}"
            )
            return False

        learners = []
        for replica in accepts:
            if replica.receive_learn(proposal_number, operation):
                learners.append(replica)

        if len(learners) < majority:
            self._write_log(
                f"Node {self.replica_id}: ABORT {self._describe(operation)}, "
                f"proposal #{proposal_number}, learns {len(learners)}/{majority}"
            )
            return False

        if self.apply_callback:
            self.apply_callback(operation)
        for replica in self.peers:
            replica.commit(proposal_number, operation)

        self._write_log(
            f"Node {self.replica_id}: COMMIT {self._describe(operation)}, "
            f"proposal #{proposal_number}, majority {len(learners)}/{len(self.peers)}"
        )
        return True

    def receive_accept(self, proposal_number, operation, leader_id=None):
        """Handle ACCEPT message from leader."""
        with self.lock:
            if proposal_number < self.accepted_number:
                return False
            self.accepted_number = proposal_number
            self.accepted_value = operation
        leader_text = f" from leader {leader_id}" if leader_id is not None else ""
        self._write_log(
            f"Node {self.replica_id}: ACCEPT{leader_text} "
            f"{self._describe(operation)}, proposal #{proposal_number}"
        )
        return True

    def receive_learn(self, proposal_number, operation):
        """Handle LEARN message from replica."""
        if proposal_number != self.accepted_number:
            return False
        self._write_log(
            f"Node {self.replica_id}: LEARN {self._describe(operation)}, "
            f"proposal #{proposal_number}"
        )
        return True

    def commit(self, proposal_number, operation):
        entry = {
            "proposal_number": proposal_number,
            "operation": operation,
        }
        self.log.append(entry)

    def is_leader(self):
        return self.leader == self.replica_id

    def _leader_replica(self):
        for replica in self.peers:
            if replica.replica_id == self.leader:
                return replica
        raise RuntimeError("Paxos leader is not configured")

    def _describe(self, operation):
        op = operation.get("op", "unknown")
        filename = operation.get("filename")
        output = operation.get("output_filename")
        page = operation.get("page") or {}
        guid = page.get("guid") or operation.get("guid")
        details = [op]
        if filename:
            details.append(str(filename))
        if output:
            details.append(f"-> {output}")
        if guid:
            details.append(f"page {guid}")
        return " ".join(details)

    def _write_log(self, message):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")


def create_local_paxos_cluster(num_replicas=3, leader_id=1, log_path="storage/paxos_log.txt"):
    """Create a fixed-leader in-process Paxos cluster."""
    if num_replicas < 3:
        raise ValueError("num_replicas must be at least 3")
    replicas = [
        PaxosReplica(replica_id=idx + 1, log_path=log_path)
        for idx in range(num_replicas)
    ]
    for replica in replicas:
        replica.configure_cluster(replicas, leader_id=leader_id)
    return replicas
