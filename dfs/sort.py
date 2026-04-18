"""
Distributed sorting for DFS files.
"""
import hashlib

from dfs.api import DFS


class DistributedSorter:
    def __init__(self, dfs: DFS):
        self.dfs = dfs

    def sort_file(self, filename, output_filename):
        """Read, partition by Chord successor, locally sort, and write output."""
        meta = self.dfs._get_metadata(filename)
        if not meta:
            return False

        buckets = {
            node.node_id: []
            for node in sorted(self.dfs.chord.ring, key=lambda item: item.node_id)
        }
        for page_desc in meta.pages:
            page_data = self.dfs.chord.get(page_desc["guid"])
            if not page_data:
                continue
            try:
                lines = page_data.decode().splitlines()
            except UnicodeDecodeError:
                return False
            for line in lines:
                if "," not in line:
                    continue
                key, value = line.split(",", 1)
                route_key = hashlib.sha1(key.encode()).hexdigest()
                owner = self.dfs.chord.locate_successor(route_key)
                buckets[owner.node_id].append((key, value))

        records = []
        for node_id in sorted(buckets):
            local_records = sorted(buckets[node_id], key=lambda record: record[0])
            records.extend(local_records)
        if not records:
            return False

        records.sort(key=lambda record: record[0])
        output_content = ("\n".join([f"{key},{value}" for key, value in records]) + "\n").encode()
        return self.dfs._write_bytes(output_filename, output_content)
