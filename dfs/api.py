# dfs/api.py
"""
DFS API: touch, append, read, ls, stat
"""
import json

from chord.node import ChordNode
from dfs.metadata import Metadata
from dfs.page import Page
from replication.paxos import PaxosReplica


class DFS:
    def __init__(self, chord_node: ChordNode, paxos_replica: PaxosReplica = None):
        self.chord = chord_node
        self.paxos = paxos_replica

    def touch(self, filename):
        """Create an empty file in the DFS (replicated if Paxos enabled)."""
        meta = Metadata(filename)
        key = meta.get_metadata_key()
        if self.paxos:
            self.paxos.propose({"op": "touch", "filename": filename, "meta": meta.to_json()})
        else:
            self.chord.put(key, meta.to_json())


    def append(self, filename, local_path):
        """Append a local file as a new page to the DFS file (replicated if Paxos enabled)."""
        with open(local_path, 'rb') as f:
            content = f.read()
        meta_key = Metadata(filename).get_metadata_key()
        meta_json = self.chord.get(meta_key)
        if meta_json:
            meta = Metadata.from_json(meta_json)
        else:
            meta = Metadata(filename)
        page_no = meta.num_pages
        page = Page(filename, page_no, content)
        page_key = page.guid
        if self.paxos:
            self.paxos.propose({"op": "append", "filename": filename, "page": page.to_dict(), "content": content.hex()})
        else:
            self.chord.put(page_key, content)
            meta.pages.append(page.to_dict())
            meta.num_pages += 1
            meta.size_bytes += len(content)
            meta.version += 1
            self.chord.put(meta_key, meta.to_json())


    def read(self, filename):
        """Read the entire file from DFS."""
        meta_key = Metadata(filename).get_metadata_key()
        meta_json = self.chord.get(meta_key)
        if not meta_json:
            return None
        meta = Metadata.from_json(meta_json)
        content = b''
        for page_desc in meta.pages:
            page_data = self.chord.get(page_desc['guid'])
            if page_data:
                content += page_data
        return content


    def ls(self):
        """List all files in the DFS."""
        # This is a placeholder; actual implementation may require a file index
        # For now, assume a special key 'file_index' stores all filenames
        index = self.chord.get('file_index')
        if index:
            return json.loads(index)
        return []


    def stat(self, filename):
        """Return file metadata."""
        meta_key = Metadata(filename).get_metadata_key()
        meta_json = self.chord.get(meta_key)
        if not meta_json:
            return None
        meta = Metadata.from_json(meta_json)
        return meta.__dict__

    def head(self, filename, n):
        """Return the first n bytes of the file."""
        content = self.read(filename)
        if content:
            return content[:n]
        return None

    def tail(self, filename, n):
        """Return the last n bytes of the file."""
        content = self.read(filename)
        if content:
            return content[-n:]
        return None

    def delete_file(self, filename):
        """Delete a file and its pages from the DFS (replicated if Paxos enabled)."""
        meta_key = Metadata(filename).get_metadata_key()
        meta_json = self.chord.get(meta_key)
        if not meta_json:
            return False
        meta = Metadata.from_json(meta_json)
        if self.paxos:
            self.paxos.propose({"op": "delete_file", "filename": filename, "pages": [p['guid'] for p in meta.pages]})
        else:
            for page_desc in meta.pages:
                self.chord.delete(page_desc['guid'])
            self.chord.delete(meta_key)
            # Remove from file index if used
            index = self.chord.get('file_index')
            if index:
                files = json.loads(index)
                if filename in files:
                    files.remove(filename)
                    self.chord.put('file_index', json.dumps(files))
        return True
