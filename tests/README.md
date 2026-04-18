# tests/

This directory contains sample input files, output validation scripts, and instructions for testing the DFS implementation.

- `sample_input.txt`: Example input for distributed sorting.
- `validate_sorted.py`: Script to check if a file is sorted by key.

## Usage

1. Upload `sample_input.txt` to the DFS using the CLI or API.
2. Run distributed sort to produce an output file.
3. Download the output and run:

    python tests/validate_sorted.py <output_file>

4. Check Paxos logs in storage/ for replication evidence.
