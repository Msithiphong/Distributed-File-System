# DESIGN.md

## Chord Integration
- Chord is used for deterministic placement and retrieval of metadata and pages.
- Each file's metadata and pages are stored using hash-derived keys.
- The default CLI creates 5 in-process Chord peers and routes `put`, `get`, and
  `delete` through `locate_successor`.

## Metadata and Page Design
- Metadata tracks filename, size, number of pages, page GUIDs, and version.
- Pages store file content and are referenced in metadata.

## Distributed Sorting Strategy
- Records are read from DFS pages, parsed as `key,value`, and routed to the
  Chord successor of `hash(key)`.
- Each responsible peer maintains a locally sorted bucket. Buckets are assembled
  and globally ordered before the output is written as a new DFS file.
- The sorted output is stored through the DFS write path, so metadata and pages
  are replicated through Paxos before being placed through Chord.

## Replication Strategy
- Metadata operations are replicated using a simplified Paxos protocol.
- The default CLI creates 3 in-process Paxos replicas with a fixed leader.
- Mutating DFS operations (`touch`, `append`, `delete_file`, and sort output
  writes) are proposed to Paxos before the committed operation is applied to
  Chord storage.

## Paxos Message Flow
- Leader proposes an operation.
- Replicas receive ACCEPT, respond with LEARN.
- Operation is committed once a majority has learned it.
- `storage/paxos_log.txt` records PROPOSE, ACCEPT, LEARN, and COMMIT messages
  with proposal numbers and operation details.

## Failure Assumptions
- Crash failures only, no Byzantine behavior.
- Messages may be delayed, lost, duplicated, or reordered.

## Limitations and Future Improvements
- The current topology is in-process rather than separate networked processes.
- Page descriptors record intended replica ownership, while storage is routed
  through the in-process Chord ring.
- Further optimizations and robustness can be added.
