# dfs/metadata.py
"""
Metadata object for DFS files.
"""
import json
import hashlib

class Metadata:
    def __init__(self, filename):
        self.filename = filename
        self.size_bytes = 0
        self.num_pages = 0
        self.pages = []  # List of page descriptors: {page_no, guid}
        self.version = 1

    def get_metadata_key(self):
        return hashlib.sha1(f"metadata:{self.filename}".encode()).hexdigest()

    def to_json(self):
        return json.dumps({
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "num_pages": self.num_pages,
            "pages": self.pages,
            "version": self.version
        })

    @staticmethod
    def from_json(data):
        obj = json.loads(data)
        meta = Metadata(obj["filename"])
        meta.size_bytes = obj["size_bytes"]
        meta.num_pages = obj["num_pages"]
        meta.pages = obj["pages"]
        meta.version = obj["version"]
        return meta
