# chord/node.py
"""
Chord node implementation, finger table logic, and routing operations.
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
        node.finger_table = [node.successor]
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

    def locate_successor(self, key):
        """Find the successor node for a given key."""
        key_id = key_to_id(key)
        ring = sorted(self.ring, key=lambda node: node.node_id)
        for node in ring:
            if key_id <= node.node_id:
                return node
        return ring[0]

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

    # ...other Chord operations...
