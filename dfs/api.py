"""
DFS API: touch, append, read, head, tail, delete_file, ls, stat, sort_file.
"""
import json

from chord.node import ChordNode
from dfs.metadata import Metadata
from dfs.page import Page
from replication.paxos import PaxosReplica


class DFS:
    DEFAULT_REPLICATION_FACTOR = 3

    def __init__(
        self,
        chord_node: ChordNode,
        paxos_replica: PaxosReplica = None,
        replication_factor=DEFAULT_REPLICATION_FACTOR,
    ):
        self.chord = chord_node
        self.paxos = paxos_replica
        self.replication_factor = replication_factor
        if self.paxos:
            self.paxos.set_apply_callback(self._apply_committed_operation)

    def touch(self, filename):
        """Create an empty file in the DFS."""
        meta = Metadata(filename)
        if self._get_metadata(filename):
            return False
        return self._commit_or_apply(
            {
                "op": "touch",
                "filename": filename,
                "meta": meta.to_json(),
            }
        )

    def append(self, filename, local_path):
        """Append a local file as a new page to the DFS file."""
        with open(local_path, "rb") as file_obj:
            return self._append_bytes(filename, file_obj.read())

    def read(self, filename):
        """Read the entire file from DFS."""
        meta = self._get_metadata(filename)
        if not meta:
            return None
        content = b""
        for page_desc in meta.pages:
            page_data = self.chord.get_replicated(
                page_desc["guid"],
                count=self.replication_factor,
            )
            if page_data is not None:
                content += page_data
        return content

    def head(self, filename, n):
        """Return the first n bytes of the file."""
        content = self.read(filename)
        if content is not None:
            return content[:n]
        return None

    def tail(self, filename, n):
        """Return the last n bytes of the file."""
        content = self.read(filename)
        if content is not None:
            if n == 0:
                return b""
            return content[-n:]
        return None

    def delete_file(self, filename):
        """Delete a file and its pages from the DFS."""
        meta = self._get_metadata(filename)
        if not meta:
            return False
        return self._commit_or_apply(
            {
                "op": "delete_file",
                "filename": filename,
                "pages": [page["guid"] for page in meta.pages],
            }
        )

    def ls(self):
        """List all files in the DFS."""
        return self._get_file_index()

    def stat(self, filename):
        """Return file metadata."""
        meta = self._get_metadata(filename)
        if not meta:
            return None
        return dict(meta.__dict__)

    def sort_file(self, filename, output_filename):
        """Sort a DFS file into another DFS file."""
        from dfs.sort import DistributedSorter

        return DistributedSorter(self).sort_file(filename, output_filename)

    def _write_bytes(self, filename, content):
        """Replace a DFS file with one page of bytes using the normal DFS path."""
        if self._get_metadata(filename):
            self.delete_file(filename)
        self.touch(filename)
        return self._append_bytes(filename, content)

    def _append_bytes(self, filename, content):
        meta = self._get_metadata(filename) or Metadata(filename)
        page = Page(filename, meta.num_pages, content)
        return self._commit_or_apply(
            {
                "op": "append",
                "filename": filename,
                "page_no": page.page_no,
                "guid": page.guid,
                "content": content.hex(),
            }
        )

    def _commit_or_apply(self, operation):
        if self.paxos:
            return self.paxos.propose(operation)
        self._apply_committed_operation(operation)
        return True

    def _apply_committed_operation(self, operation):
        op = operation["op"]
        if op == "touch":
            self._apply_touch(operation)
        elif op == "append":
            self._apply_append(operation)
        elif op == "delete_file":
            self._apply_delete_file(operation)
        else:
            raise ValueError(f"Unknown DFS operation: {op}")

    def _apply_touch(self, operation):
        filename = operation["filename"]
        meta = self._get_metadata(filename)
        if meta is None:
            meta = Metadata.from_json(operation["meta"])
        self._put_metadata(meta)
        self._add_to_file_index(filename)

    def _apply_append(self, operation):
        filename = operation["filename"]
        content = bytes.fromhex(operation["content"])
        meta = self._get_metadata(filename) or Metadata(filename)
        page_guid = operation["guid"]
        page_desc = self._page_descriptor_for(operation["page_no"], page_guid)

        self.chord.put_replicated(
            page_guid,
            content,
            count=self.replication_factor,
        )

        existing_page = next(
            (page for page in meta.pages if page["guid"] == page_guid),
            None,
        )
        if existing_page is None:
            meta.pages.append(page_desc)
            meta.pages.sort(key=lambda page: page["page_no"])
            meta.num_pages += 1
            meta.size_bytes += len(content)
            meta.version += 1
        else:
            existing_page.update(page_desc)

        self._put_metadata(meta)
        self._add_to_file_index(filename)

    def _apply_delete_file(self, operation):
        filename = operation["filename"]
        for page_guid in operation["pages"]:
            self.chord.delete_replicated(
                page_guid,
                count=self.replication_factor,
            )
        self.chord.delete_replicated(
            Metadata(filename).get_metadata_key(),
            count=self.replication_factor,
        )
        self._remove_from_file_index(filename)

    def _get_metadata(self, filename):
        meta_json = self.chord.get_replicated(
            Metadata(filename).get_metadata_key(),
            count=self.replication_factor,
        )
        if meta_json is None:
            return None
        return Metadata.from_json(meta_json)

    def _get_file_index(self):
        index = self.chord.get_replicated(
            "file_index",
            count=self.replication_factor,
        )
        if index is not None:
            return json.loads(index)
        return []

    def _add_to_file_index(self, filename):
        files = self._get_file_index()
        if filename not in files:
            files.append(filename)
            self._store_file_index(files)

    def _remove_from_file_index(self, filename):
        files = self._get_file_index()
        if filename in files:
            files.remove(filename)
            self._store_file_index(files)

    def _store_file_index(self, files):
        files = sorted(files)
        if files:
            self.chord.put_replicated(
                "file_index",
                json.dumps(files),
                count=self.replication_factor,
            )
            return
        self.chord.delete_replicated(
            "file_index",
            count=self.replication_factor,
        )

    def _put_metadata(self, meta):
        self._refresh_metadata_replication(meta)
        self.chord.put_replicated(
            meta.get_metadata_key(),
            meta.to_json(),
            count=self.replication_factor,
        )

    def _refresh_metadata_replication(self, meta):
        meta_key = meta.get_metadata_key()
        replica_nodes = self.chord.replica_nodes_for_key(
            meta_key,
            count=self.replication_factor,
        )
        meta.metadata_owner = replica_nodes[0].node_id if replica_nodes else None
        meta.metadata_replicas = [node.node_id for node in replica_nodes]

    def _page_descriptor_for(self, page_no, page_guid):
        replica_nodes = self.chord.replica_nodes_for_key(
            page_guid,
            count=self.replication_factor,
        )
        owner = replica_nodes[0] if replica_nodes else None
        return {
            "page_no": page_no,
            "guid": page_guid,
            "owner": owner.node_id if owner else None,
            "replicas": [node.node_id for node in replica_nodes],
        }

    def _replica_ids_for_key(self, key, count=3):
        return [
            node.node_id
            for node in self.chord.replica_nodes_for_key(key, count=count)
        ]
