# client/cli.py
"""
Simple CLI for DFS operations (Milestone 1).
"""
from chord.node import ChordNode
from dfs.api import DFS

if __name__ == "__main__":
    # Example: create a Chord node and DFS instance
    node = ChordNode(node_id=1, address=("127.0.0.1", 5000))
    dfs = DFS(node)
    # Example usage (expand as needed):
    # dfs.touch("example.txt")
    # dfs.append("example.txt", "./localfile.txt")
    # print(dfs.read("example.txt"))
    pass
