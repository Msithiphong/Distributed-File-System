# Distributed File System (DFS) on Chord

This project implements a distributed file system on top of a Chord-based DHT, supporting page-based storage, distributed sorting, and metadata replication using Paxos.

## Features
- Distributed file storage with Chord lookups
- Page-based file metadata management
- Distributed sorting of file contents
- Metadata replication with simplified Paxos

## Usage
- Use the CLI in client/ to interact with the DFS
- See tests/README.md for testing and validation instructions

## Design
See DESIGN.md for a detailed design report.

## Testing the Functionality

### Running the CLI

1. Open a terminal in the project root directory.
2. Run the CLI using:
	```
	python -m client.cli
	```
	(Note: The CLI currently contains example code. To test, uncomment or add commands in `client/cli.py`.)

### Example DFS Operations

In `client/cli.py`, you can use:

```python
dfs.touch("example.txt")
dfs.append("example.txt", "../tests/sample_input.txt")
print(dfs.read("example.txt").decode())
print(dfs.ls())
print(dfs.stat("example.txt"))
```

### Distributed Sort Test

1. Upload `tests/sample_input.txt` to the DFS as a file (e.g., `example.txt`).
2. Use the distributed sort function (see `dfs/sort.py`) to sort the file and write the output as a new DFS file.
3. Download the sorted output and validate it:
	```
	python tests/validate_sorted.py <downloaded_output_file>
	```

### Paxos Log and Replication

Check `storage/paxos_log.txt` for example Paxos message flow and replication evidence.
