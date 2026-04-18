# tests/validate_sorted.py
"""
Check that a file's records are sorted by key.
"""
import sys

def is_sorted(filename):
    with open(filename, 'r') as f:
        prev = None
        for line in f:
            if ',' not in line:
                continue
            key, _ = line.strip().split(',', 1)
            if prev is not None and key < prev:
                return False
            prev = key
    return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_sorted.py <output_file>")
        sys.exit(1)
    if is_sorted(sys.argv[1]):
        print("File is sorted.")
    else:
        print("File is NOT sorted.")
