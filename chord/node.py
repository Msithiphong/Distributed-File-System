"""
Chord node implementation, finger table logic, routing operations, and
successor-based replication helpers.
"""
import hashlib


RING_BITS = 160
RING_SIZE = 2 ** RING_BITS


def key_to_id(key):
    """Map an arbitrary Chord key to the identifier ring."""
    if isinstance(key, int):
        return key % RING_SIZE
    key_text = str(key)
    try:
        if len(key_text) == 40:
            return int(key_text, 16) % RING_SIZE
    except ValueError:
        pass
    return int(hashlib.sha1(key_text.encode()).hexdigest(), 16)


def create_local_chord_ring(num_nodes=5, host="127.0.0.1", base_port=5000):
    """Create an in-process Chord ring for local DFS testing."""
    if num_nodes < 1:
        raise ValueError("num_nodes must be at least 1")

    step = RING_SIZE // num_nodes
    nodes = [
        ChordNode(node_id=(idx * step), address=(host, base_port + idx))
        for idx in range(num_nodes)
    ]
    nodes.sort(key=lambda node: node.node_id)
    for idx, node in enumerate(nodes):
        node.ring = nodes
        node.successor = nodes[(idx + 1) % len(nodes)]
        node.predecessor = nodes[(idx - 1) % len(nodes)]
    for node in nodes:
        node.finger_table = node.build_finger_table()
    return nodes


class ChordNode:
    def __init__(self, node_id, address):
        self.node_id = node_id
        self.address = address
        self.finger_table = []
        self.successor = None
        self.predecessor = None
        self.ring = [self]
        self._store = {}

    def _sorted_ring(self):
        return sorted(self.ring, key=lambda node: node.node_id)

    def _successor_for_id(self, key_id):
        ring = self._sorted_ring()
        for node in ring:
            if key_id <= node.node_id:
                return node
        return ring[0]

    def build_finger_table(self):
        """Build a full Chord finger table for local inspection and routing."""
        return [
            self._successor_for_id((self.node_id + (1 << offset)) % RING_SIZE)
            for offset in range(RING_BITS)
        ]

    def locate_successor(self, key):
        """Find the successor node responsible for a given key."""
        return self._successor_for_id(key_to_id(key))

    def replica_nodes_for_key(self, key, count=3):
        """Return the owner and successor replicas for a key."""
        if count <= 0:
            return []
        ring = self._sorted_ring()
        owner = self.locate_successor(key)
        owner_index = ring.index(owner)
        replica_count = min(count, len(ring))
        return [
            ring[(owner_index + offset) % len(ring)]
            for offset in range(replica_count)
        ]

    def put(self, key, value):
        """Store a value at the node responsible for the key."""
        node = self.locate_successor(key)
        node._store[key] = value
        return node

    def get(self, key):
        """Retrieve a value by key from the DHT."""
        node = self.locate_successor(key)
        return node._store.get(key)

    def delete(self, key):
        """Delete a value by key from the DHT."""
        node = self.locate_successor(key)
        return node._store.pop(key, None) is not None

    def put_replicated(self, key, value, count=3):
        """Store the same key/value on the owner and successor replicas."""
        replica_nodes = self.replica_nodes_for_key(key, count=count)
        for node in replica_nodes:
            node._store[key] = value
        return replica_nodes

    def get_replicated(self, key, count=3):
        """Retrieve a replicated value from the owner or any successor copy."""
        for node in self.replica_nodes_for_key(key, count=count):
            if key in node._store:
                return node._store[key]
        return None

    def delete_replicated(self, key, count=3):
        """Delete every replicated copy of a key."""
        removed = False
        for node in self.replica_nodes_for_key(key, count=count):
            if key in node._store:
                del node._store[key]
                removed = True
        return removed

    def finger_table_summary(self):
        """Return the finger table as a compact list of node IDs."""
        summary = []
        for node in self.finger_table:
            if not summary or summary[-1] != node.node_id:
                summary.append(node.node_id)
        return summary

    def ring_summary(self):
        """Return demo-friendly ring information for every node."""
        return [
            {
                "node_id": node.node_id,
                "predecessor": (
                    node.predecessor.node_id if node.predecessor else None
                ),
                "successor": node.successor.node_id if node.successor else None,
                "address": node.address,
                "finger_table": node.finger_table_summary(),
            }
            for node in self._sorted_ring()
        ]
