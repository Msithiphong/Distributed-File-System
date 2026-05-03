# DESIGN.md

## Overview

This DFS keeps the assignment architecture in-process:

```text
CLI -> DFS API -> Paxos leader/replicas -> Chord ring -> per-node local stores
```

The goal is to make the distributed behavior visible and testable without adding sockets, multiprocessing, or third-party dependencies.

## Chord Layer

- The ring contains 5 in-process `ChordNode` objects by default.
- Keys live on the successor of their SHA-1 identifier.
- Each node builds a full finger table for inspection and demo output.
- Successor-based replication uses the owner plus the next two successors (`R = 3`).

Supported storage modes:

- `put/get/delete` for single-owner Chord placement
- `put_replicated/get_replicated/delete_replicated` for DFS data that must survive one missing replica copy

## DFS Data Model

Per-file metadata is stored under:

```text
sha1("metadata:<filename>")
```

Each append creates one page stored under:

```text
sha1("<filename>:<page_no>")
```

Metadata includes:

- filename
- size in bytes
- page count
- ordered page descriptors
- version
- metadata owner
- metadata replica IDs

Each page descriptor includes:

- `page_no`
- `guid`
- `owner`
- `replicas`

The file listing is stored separately as replicated metadata under `file_index`.

## Replication Strategy

The DFS replicates all user-visible storage objects:

- metadata JSON
- file pages
- file index

Replica placement is deterministic:

1. Locate the Chord owner for the key.
2. Select the owner and the next two successors in ring order.
3. Store identical copies on those three nodes.

Reads use `get_replicated()` so a missing owner copy can still be served by a successor replica.

## Paxos Layer

The Paxos cluster contains 3 in-process replicas with a fixed leader.

For each replicated DFS mutation:

1. The leader assigns a proposal number.
2. Replicas receive `ACCEPT`.
3. Accepting replicas send `LEARN`.
4. The leader commits after a majority learns the proposal.
5. Every active replica applies the committed operation in proposal order.

Crash handling:

- Replicas support crash-stop behavior through `crash()` and `recover()`.
- Inactive replicas ignore `ACCEPT`, `LEARN`, and `COMMIT`.
- A recovered follower catches up by replaying missing committed log entries from the leader.

Because all replicas share one in-process DFS/Chord state in this assignment version, DFS mutation callbacks must be idempotent.

## CLI Demo Surface

The CLI keeps the original DFS commands and adds:

- `topology` to print node IDs, neighbors, addresses, finger tables, and Paxos leader info
- `paxos_log [n]` to inspect recent evidence from `storage/paxos_log.txt`
- `failure_demo` to crash one follower, commit a metadata update with a 2/3 majority, recover the follower, and replay missed operations

## Limitations

- The system is simulated in one Python process, not over a network.
- Chord routing remains deterministic and local rather than message-driven.
- Durable recovery for Chord data and DFS state is not implemented.
