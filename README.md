# Distributed File System (DFS) on Chord

This project implements a Distributed File System on top of a Chord-style DHT. The default CLI runs an in-process distributed topology so the full required path is exercised without starting separate network processes:

```text
DFS Client CLI -> DFS API -> Paxos Replication -> Chord Routing -> Local Storage/Logs
```

## Features

- Interactive DFS CLI launched with `python -m client.cli`
- Required DFS operations: `touch`, `append`, `read`, `head`, `tail`, `delete_file`, `ls`, and `stat`
- Distributed sorting with `sort_file`
- 5 in-process Chord peers with deterministic successor routing
- 3 in-process Paxos replicas with fixed leader, proposal numbers, `ACCEPT`, `LEARN`, and majority `COMMIT`
- Human-readable Paxos evidence in `storage/paxos_log.txt`

## Architecture

The CLI is intentionally thin: it parses commands and calls the DFS API. Mutating DFS operations are proposed through Paxos before committed metadata and page operations are applied through Chord routing.

Default local topology:

```text
5 Chord peers
3 Paxos replicas
1 DFS client entry point
```

Mutating operations that go through Paxos:

- `touch`
- `append`
- `delete_file`
- `sort_file` output writes
- metadata/index updates caused by those operations

Reads such as `read`, `head`, `tail`, `ls`, and `stat` read committed state through DFS and Chord.

See `DESIGN.md` for the design report.

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
help [command]
exit
quit
```

## Example Workflow

```text
dfs> touch example.txt
dfs> append example.txt tests/sample_input.txt
dfs> read example.txt
dfs> head example.txt 20
dfs> tail example.txt 20
dfs> ls
dfs> stat example.txt
```

`stat` includes metadata such as file size, page count, page GUIDs, Chord owner, and intended replica IDs.

## Distributed Sort Workflow

```text
dfs> touch example.txt
dfs> append example.txt tests/sample_input.txt
dfs> sort_file example.txt sorted.txt
dfs> read sorted.txt --output tests/sorted_output.txt
```

Then validate from the project root:

```bash
python tests/validate_sorted.py tests/sorted_output.txt
```

Sorting reads DFS pages, parses `key,value` records, routes records by Chord successor of `hash(key)`, sorts local buckets, assembles the globally sorted output, and writes the result back through the DFS/Paxos path.

## Paxos Logs

After running mutating CLI commands, inspect:

```text
storage/paxos_log.txt
```

The log contains real runtime evidence such as:

```text
Node 1: PROPOSE touch example.txt, proposal #1
Node 2: ACCEPT from leader 1 touch example.txt, proposal #1
Node 3: LEARN touch example.txt, proposal #1
Node 1: COMMIT touch example.txt, proposal #1, majority 3/3
```

## Tests

Run all tests:

```bash
python -m unittest discover -s tests
```

The test suite covers:

- Chord successor routing across 5 peers
- Paxos proposal numbers, majority commit, ordered replica logs, and log evidence
- DFS mutation flow through Paxos and Chord storage
- CLI command workflow and distributed sorting


## External Libraries

This project uses only Python standard library modules and does not require any external (third-party) libraries. All dependencies are included with a standard Python 3 installation. No additional installation via pip is necessary.

## Notes And Limitations

- The topology is in-process for this assignment version; it does not require sockets or multiple terminal processes.
- The implementation demonstrates the required architecture and protocol concepts, but durable crash recovery is not implemented.
- `storage/paxos_log.txt` is append-only during normal CLI runs; delete it manually before a fresh evidence run if you want a clean log.
