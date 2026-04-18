# dfs/page.py
"""
Page object for DFS files.
"""
import hashlib

class Page:
    def __init__(self, filename, page_no, content):
        self.filename = filename
        self.page_no = page_no
        self.content = content
        self.guid = self.get_page_guid()

    def get_page_guid(self):
        return hashlib.sha1(f"{self.filename}:{self.page_no}".encode()).hexdigest()

    def to_dict(self):
        return {
            "page_no": self.page_no,
            "guid": self.guid
        }
