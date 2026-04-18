# dfs/sort.py
"""
Distributed sorting for DFS files.
"""
from dfs.api import DFS
from dfs.metadata import Metadata
import json

class DistributedSorter:
    def __init__(self, dfs: DFS):
        self.dfs = dfs

    def sort_file(self, filename, output_filename):
        """Distributed sort: read, partition, aggregate, and write sorted output."""
        # 1. Read all pages and parse records
        meta = Metadata(filename)
        meta_key = meta.get_metadata_key()
        meta_json = self.dfs.chord.get(meta_key)
        if not meta_json:
            return False
        meta = Metadata.from_json(meta_json)
        records = []
        for page_desc in meta.pages:
            page_data = self.dfs.chord.get(page_desc['guid'])
            if page_data:
                lines = page_data.decode().splitlines()
                for line in lines:
                    if ',' in line:
                        key, value = line.split(',', 1)
                        records.append((key, value))
        # 2. Sort all records (simulate distributed aggregation)
        records.sort(key=lambda x: x[0])
        # 3. Write sorted output as new DFS file
        # (For simplicity, one page; can split if large)
        output_content = '\n'.join([f"{k},{v}" for k, v in records]).encode()
        self.dfs.touch(output_filename)
        # Write as a single page
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(output_content)
            tmp_path = tmp.name
        self.dfs.append(output_filename, tmp_path)
        return True
