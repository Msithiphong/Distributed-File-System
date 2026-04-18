# DESIGN.md

## Chord Integration
- Chord is used for deterministic placement and retrieval of metadata and pages.
- Each file's metadata and pages are stored using hash-derived keys.

## Metadata and Page Design
- Metadata tracks filename, size, number of pages, page GUIDs, and version.
- Pages store file content and are referenced in metadata.

## Distributed Sorting Strategy
- Records are read from all pages, parsed, and routed by key.
- Sorting is performed globally and output is written as a new DFS file.

## Replication Strategy
- Metadata operations are replicated using a simplified Paxos protocol.
- At least 3 replicas are used for majority-based commitment.

## Paxos Message Flow
- Leader proposes an operation.
- Replicas receive ACCEPT, respond with LEARN.
- Operation is committed once a majority has learned it.

## Failure Assumptions
- Crash failures only, no Byzantine behavior.
- Messages may be delayed, lost, duplicated, or reordered.

## Limitations and Future Improvements
- Page replication is not yet implemented.
- Networking and concurrency are simplified.
- Further optimizations and robustness can be added.
