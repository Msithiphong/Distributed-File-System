# tests/

This directory contains sample data, validation helpers, and tests for the DFS + Paxos architecture.

## Files

- `sample_input.txt`: sample `key,value` records for distributed sorting.
- `validate_sorted.py`: validates that an output file is sorted by key.
- `test_architecture.py`: verifies Chord routing, Paxos majority/order/logging, and DFS mutation flow.
- `test_cli.py`: verifies the interactive CLI command workflow against the default replicated topology.
- `sorted_output.txt`: optional generated output from manual CLI sort validation.

## Manual CLI Validation

Start the CLI from the project root:

```bash
python -m client.cli
```

The default CLI creates:

```text
5 in-process Chord peers
3 in-process Paxos replicas
```

Run the workflow:

```text
dfs> touch example.txt
dfs> append example.txt tests/sample_input.txt
dfs> stat example.txt
dfs> sort_file example.txt sorted.txt
dfs> read sorted.txt --output tests/sorted_output.txt
dfs> exit
```

Validate the downloaded sorted output:

```bash
python tests/validate_sorted.py tests/sorted_output.txt
```

Expected result:

```text
File is sorted.
```

## Paxos Evidence

After the CLI workflow, inspect:

```text
storage/paxos_log.txt
```

The log should include `PROPOSE`, `ACCEPT`, `LEARN`, and `COMMIT` entries for mutating DFS operations such as `touch`, `append`, and the output writes caused by `sort_file`.

## Automated Tests

Run all tests from the project root:

```bash
python -m unittest discover -s tests
```

The automated tests confirm:

- `put`, `get`, and `delete` route through the Chord successor owner.
- Paxos commits after a majority of 3 replicas learns an operation.
- Paxos replica logs preserve committed operation order.
- DFS mutations are applied to Chord only after Paxos commit.
- CLI operations use the same 5-peer/3-replica topology as manual runs.

## Clean Evidence Runs

`storage/paxos_log.txt` is append-only. For a clean manual run, delete the log before starting the CLI:

```powershell
Remove-Item storage/paxos_log.txt
```

The file will be recreated when the next mutating DFS operation is committed.
