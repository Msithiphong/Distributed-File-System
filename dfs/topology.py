"""
Local in-process topology for the DFS CLI and tests.
"""
from dataclasses import dataclass

from chord.node import create_local_chord_ring
from dfs.api import DFS
from replication.paxos import create_local_paxos_cluster


@dataclass
class LocalDFSTopology:
    dfs: DFS
    chord_nodes: list
    paxos_replicas: list


def create_local_dfs_topology(
    num_chord_nodes=5,
    num_paxos_replicas=3,
    log_path="storage/paxos_log.txt",
    replication_factor=DFS.DEFAULT_REPLICATION_FACTOR,
):
    chord_nodes = create_local_chord_ring(num_nodes=num_chord_nodes)
    paxos_replicas = create_local_paxos_cluster(
        num_replicas=num_paxos_replicas,
        leader_id=1,
        log_path=log_path,
    )
    dfs = DFS(
        chord_nodes[0],
        paxos_replica=paxos_replicas[0],
        replication_factor=replication_factor,
    )
    for replica in paxos_replicas:
        replica.set_apply_callback(dfs._apply_committed_operation)
    return LocalDFSTopology(
        dfs=dfs,
        chord_nodes=chord_nodes,
        paxos_replicas=paxos_replicas,
    )
