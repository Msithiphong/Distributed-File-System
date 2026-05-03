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
        self.active = True
        self._committed_proposals = set()
        self._applied_proposals = set()
        self.lock = threading.Lock()

    def configure_cluster(self, replicas, leader_id=1):
        self.peers = replicas
        self.leader = leader_id

    def set_apply_callback(self, callback):
        self.apply_callback = callback

    def propose(self, operation):
        """Propose an operation as leader and commit after a majority learns it."""
        if not self.active:
            self._write_log(
                f"Node {self.replica_id}: ABORT inactive proposer "
                f"{self._describe(operation)}"
            )
            return False
        if not self.is_leader():
            leader = self._leader_replica()
            if not leader.active:
                self._write_log(
                    f"Node {self.replica_id}: ABORT leader {leader.replica_id} inactive "
                    f"{self._describe(operation)}"
                )
                return False
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

        for replica in self.peers:
            replica.commit(proposal_number, operation)

        self._write_log(
            f"Node {self.replica_id}: COMMIT {self._describe(operation)}, "
            f"proposal #{proposal_number}, majority {len(learners)}/{len(self.peers)}"
        )
        return True

    def receive_accept(self, proposal_number, operation, leader_id=None):
        """Handle ACCEPT message from leader."""
        if not self.active:
            self._write_log(
                f"Node {self.replica_id}: SKIP ACCEPT inactive "
                f"{self._describe(operation)}, proposal #{proposal_number}"
            )
            return False
        with self.lock:
            if proposal_number < self.accepted_number:
                self._write_log(
                    f"Node {self.replica_id}: REJECT ACCEPT "
                    f"{self._describe(operation)}, proposal #{proposal_number}"
                )
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
        if not self.active:
            self._write_log(
                f"Node {self.replica_id}: SKIP LEARN inactive "
                f"{self._describe(operation)}, proposal #{proposal_number}"
            )
            return False
        if proposal_number != self.accepted_number:
            return False
        self._write_log(
            f"Node {self.replica_id}: LEARN {self._describe(operation)}, "
            f"proposal #{proposal_number}"
        )
        return True

    def commit(self, proposal_number, operation):
        if not self.active:
            self._write_log(
                f"Node {self.replica_id}: SKIP COMMIT inactive "
                f"{self._describe(operation)}, proposal #{proposal_number}"
            )
            return False
        entry = {
            "proposal_number": proposal_number,
            "operation": operation,
        }
        with self.lock:
            self.proposal_number = max(self.proposal_number, proposal_number)
            self.accepted_number = max(self.accepted_number, proposal_number)
            if proposal_number not in self._committed_proposals:
                self.log.append(entry)
                self.log.sort(key=lambda item: item["proposal_number"])
                self._committed_proposals.add(proposal_number)
            should_apply = (
                self.apply_callback is not None
                and proposal_number not in self._applied_proposals
            )

        if should_apply:
            self.apply_callback(operation)
            with self.lock:
                self._applied_proposals.add(proposal_number)
        return True

    def crash(self):
        if not self.active:
            return
        self.active = False
        self._write_log(f"Node {self.replica_id}: CRASH")

    def recover(self):
        if self.active:
            return
        self.active = True
        self._write_log(f"Node {self.replica_id}: RECOVER")

    def sync_from(self, replica):
        if not self.active:
            self._write_log(
                f"Node {self.replica_id}: SKIP CATCH_UP inactive from replica "
                f"{replica.replica_id}"
            )
            return 0

        replayed = 0
        self._write_log(
            f"Node {self.replica_id}: CATCH_UP from replica {replica.replica_id}"
        )
        for entry in replica.log:
            proposal_number = entry["proposal_number"]
            operation = entry["operation"]
            if proposal_number in self._committed_proposals:
                continue
            self._write_log(
                f"Node {self.replica_id}: REPLAY {self._describe(operation)}, "
                f"proposal #{proposal_number} from replica {replica.replica_id}"
            )
            if self.commit(proposal_number, operation):
                replayed += 1
        self._write_log(
            f"Node {self.replica_id}: CATCH_UP complete from replica "
            f"{replica.replica_id}, replayed {replayed}"
        )
        return replayed

    def catch_up_from_leader(self):
        return self.sync_from(self._leader_replica())

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
