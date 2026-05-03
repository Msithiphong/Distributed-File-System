# Distributed File System (DFS) on Chord

This project implements an in-process distributed file system that layers DFS metadata/page management over a Chord-style DHT and serializes replicated updates with a simplified Paxos flow:

```text
DFS Client CLI -> DFS API -> Paxos Replication -> Chord Routing -> Local Storage/Logs
```

The runtime stays standard-library-only and runs in one Python process, but it now demonstrates real successor-based replication with `R = 3` for DFS metadata, file pages, and the file index.

## Features

- Interactive DFS CLI launched with `python -m client.cli`
- Required DFS operations: `touch`, `append`, `read`, `head`, `tail`, `delete_file`, `ls`, `stat`, and `sort_file`
- Demo/inspection commands: `topology`, `paxos_log`, and `failure_demo`
- 5 in-process Chord peers with deterministic ring membership and real finger tables
- Successor-based replication for metadata, page bytes, and `file_index`
- 3 in-process Paxos replicas with a fixed leader, proposal numbers, `ACCEPT`, `LEARN`, and majority `COMMIT`
- Follower crash/recovery demo with catch-up replay
- Human-readable Paxos evidence in `storage/paxos_log.txt`

## Architecture

Default local topology:

```text
5 Chord peers
3 Paxos replicas
1 DFS entry point
Replication factor R = 3
```

Storage behavior:

- File metadata is stored under `sha1("metadata:<filename>")` and replicated to the owner plus two successors.
- The file index is stored under `file_index` and replicated the same way.
- Each append creates one page stored under `sha1("<filename>:<page_no>")`, also replicated to three Chord nodes.
- `stat` exposes real metadata replica IDs and real page replica IDs.

Mutation behavior:

- `touch`
- `append`
- `delete_file`
- `sort_file` output writes

These operations commit through Paxos before active replicas apply them in proposal order. Reads (`read`, `head`, `tail`, `ls`, and `stat`) use replicated Chord lookups and can recover if one replica copy is missing.

See `DESIGN.md` for the design summary.

## Running The CLI

From the project root:

```bash
python -m client.cli
```

The shell starts with:

```text
Distributed File System CLI
Running with 5 in-process Chord peers and 3 Paxos replicas.
dfs>
```

Supported commands:

```text
touch <dfs_filename>
append <dfs_filename> <local_path>
read <dfs_filename> [--output <local_path>]
head <dfs_filename> <n>
tail <dfs_filename> <n>
delete_file <dfs_filename>
ls
stat <dfs_filename>
sort_file <input_dfs_filename> <output_dfs_filename>
topology
paxos_log [n]
failure_demo
help [command]
exit
quit
```

## Repeatable Demo

This walkthrough covers the required Chord, DFS, sorting, replication, and failure-demo features:

```text
dfs> topology
dfs> touch demo.txt
dfs> append demo.txt tests/sample_input.txt
dfs> append demo.txt tests/sample_input.txt
dfs> append demo.txt tests/sample_input.txt
dfs> read demo.txt
dfs> stat demo.txt
dfs> append records.txt tests/sample_100_records.txt
dfs> sort_file records.txt records_sorted.txt
dfs> read records_sorted.txt --output tests/records_sorted_output.txt
dfs> paxos_log 20
dfs> failure_demo
```

Then verify the 100+ record output from the project root:

```bash
python tests/validate_sorted.py tests/records_sorted_output.txt
```

What the demo shows:

- `topology` prints every Chord node ID, predecessor, successor, address, and finger table summary, plus Paxos replica IDs and the current leader.
- `stat demo.txt` shows replicated metadata and page ownership information.
- `paxos_log` prints evidence containing the leader, proposal number, `ACCEPT`, `LEARN`, and commit decision.
- `failure_demo` crashes one follower, commits a metadata update with the remaining majority, recovers the follower, and replays the missed commit.

## Sorting Workflow

`tests/sample_100_records.txt` contains 120 intentionally unsorted `key,value` records. Sorting:

1. Reads DFS pages through replicated lookups.
2. Routes records to Chord-owner buckets by `sha1(key)`.
3. Sorts bucket-local records.
4. Produces globally sorted output and writes it back through the DFS/Paxos path.

## Paxos Evidence

After mutating operations, inspect:

```text
storage/paxos_log.txt
```

Typical evidence includes:

```text
Node 1: PROPOSE touch demo.txt, proposal #1
Node 2: ACCEPT from leader 1 touch demo.txt, proposal #1
Node 3: LEARN touch demo.txt, proposal #1
Node 1: COMMIT touch demo.txt, proposal #1, majority 3/3
Node 2: CRASH
Node 2: RECOVER
Node 2: CATCH_UP from replica 1
```

## Tests

Run the full suite:

```bash
python -m unittest discover -s tests
```

The tests cover:

- Chord successor-based replication and replica fallback reads
- DFS replication of metadata, pages, and the file index
- Paxos ordered application on all active replicas
- Follower crash, majority commit, recovery, and catch-up replay
- CLI demo commands and the 100+ record sorting workflow

## External Libraries

This project uses only Python standard library modules. No third-party dependencies are required.

## Notes And Limitations

- The topology is intentionally in-process for this assignment version; it does not open sockets or spawn separate OS processes.
- Durable disk recovery is still not implemented.
- `storage/paxos_log.txt` is append-only during normal CLI runs; remove it manually if you want a fresh evidence file.
