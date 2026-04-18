"""
Interactive command-line shell for DFS operations.
"""
import cmd
import json
import shlex
from pathlib import Path

from dfs.topology import create_local_dfs_topology


class DFSShell(cmd.Cmd):
    intro = (
        "Distributed File System CLI\n"
        "Running with 5 in-process Chord peers and 3 Paxos replicas.\n"
        "Type help or ? to list commands."
    )
    prompt = "dfs> "

    def __init__(self, dfs=None):
        super().__init__()
        if dfs is None:
            topology = create_local_dfs_topology()
            dfs = topology.dfs
            self.topology = topology
        else:
            self.topology = None
        self.dfs = dfs

    def emptyline(self):
        """Do nothing for blank input instead of repeating the last command."""

    def poutput(self, message):
        print(message, file=self.stdout)

    def default(self, line):
        self.poutput(f"Unknown command: {line}")
        self.poutput("Type help or ? to list commands.")

    def _parse_args(self, arg):
        try:
            return shlex.split(arg)
        except ValueError as exc:
            self.poutput(f"Invalid arguments: {exc}")
            return None

    def _usage(self, command, usage):
        self.poutput(f"Usage: {command} {usage}".rstrip())

    def _print_bytes(self, filename, data):
        if data is None:
            self.poutput(f"File not found: {filename}")
            return
        if data == b"":
            self.poutput("")
            return
        try:
            self.poutput(data.decode("utf-8"))
        except UnicodeDecodeError:
            self.poutput(
                f"{len(data)} bytes of binary data. "
                f"Use: read {filename} --output <local_path>"
            )

    def do_touch(self, arg):
        """touch <dfs_filename> - create an empty DFS file."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 1:
            self._usage("touch", "<dfs_filename>")
            return
        created = self.dfs.touch(args[0])
        if created:
            self.poutput(f"Created {args[0]}")
        else:
            self.poutput(f"File already exists: {args[0]}")

    def do_append(self, arg):
        """append <dfs_filename> <local_path> - append a local file to DFS."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 2:
            self._usage("append", "<dfs_filename> <local_path>")
            return
        filename, local_path = args
        path = Path(local_path)
        if not path.is_file():
            self.poutput(f"Local file not found: {local_path}")
            return
        try:
            self.dfs.append(filename, str(path))
        except OSError as exc:
            self.poutput(f"Append failed: {exc}")
            return
        self.poutput(f"Appended {local_path} to {filename}")

    def do_read(self, arg):
        """read <dfs_filename> [--output <local_path>] - read a DFS file."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) not in (1, 3):
            self._usage("read", "<dfs_filename> [--output <local_path>]")
            return
        filename = args[0]
        output_path = None
        if len(args) == 3:
            if args[1] != "--output":
                self._usage("read", "<dfs_filename> [--output <local_path>]")
                return
            output_path = Path(args[2])

        data = self.dfs.read(filename)
        if data is None:
            self.poutput(f"File not found: {filename}")
            return
        if output_path:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(data)
            except OSError as exc:
                self.poutput(f"Write failed: {exc}")
                return
            self.poutput(f"Wrote {len(data)} bytes to {output_path}")
            return
        self._print_bytes(filename, data)

    def do_head(self, arg):
        """head <dfs_filename> <n> - print the first n bytes."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 2:
            self._usage("head", "<dfs_filename> <n>")
            return
        try:
            n = int(args[1])
        except ValueError:
            self.poutput("n must be an integer")
            return
        if n < 0:
            self.poutput("n must be non-negative")
            return
        self._print_bytes(args[0], self.dfs.head(args[0], n))

    def do_tail(self, arg):
        """tail <dfs_filename> <n> - print the last n bytes."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 2:
            self._usage("tail", "<dfs_filename> <n>")
            return
        try:
            n = int(args[1])
        except ValueError:
            self.poutput("n must be an integer")
            return
        if n < 0:
            self.poutput("n must be non-negative")
            return
        self._print_bytes(args[0], self.dfs.tail(args[0], n))

    def do_delete_file(self, arg):
        """delete_file <dfs_filename> - delete a DFS file and its pages."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 1:
            self._usage("delete_file", "<dfs_filename>")
            return
        if self.dfs.delete_file(args[0]):
            self.poutput(f"Deleted {args[0]}")
        else:
            self.poutput(f"File not found: {args[0]}")

    def do_ls(self, arg):
        """ls - list DFS files."""
        args = self._parse_args(arg)
        if args is None:
            return
        if args:
            self._usage("ls", "")
            return
        files = self.dfs.ls()
        if not files:
            self.poutput("No files.")
            return
        for filename in files:
            self.poutput(filename)

    def do_stat(self, arg):
        """stat <dfs_filename> - print DFS file metadata."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 1:
            self._usage("stat", "<dfs_filename>")
            return
        stat = self.dfs.stat(args[0])
        if stat is None:
            self.poutput(f"File not found: {args[0]}")
            return
        self.poutput(json.dumps(stat, indent=2, sort_keys=True))

    def do_sort_file(self, arg):
        """sort_file <input_dfs_filename> <output_dfs_filename> - sort records by key."""
        args = self._parse_args(arg)
        if args is None:
            return
        if len(args) != 2:
            self._usage("sort_file", "<input_dfs_filename> <output_dfs_filename>")
            return
        input_filename, output_filename = args
        if self.dfs.stat(input_filename) is None:
            self.poutput(f"File not found: {input_filename}")
            return
        if self.dfs.sort_file(input_filename, output_filename):
            self.poutput(f"Sorted {input_filename} into {output_filename}")
        else:
            self.poutput(
                f"Sort failed: {input_filename} has no valid key,value records"
            )

    def do_exit(self, arg):
        """exit - leave the DFS shell."""
        return True

    def do_quit(self, arg):
        """quit - leave the DFS shell."""
        return True

    def do_EOF(self, arg):
        """Exit on Ctrl+D/Ctrl+Z."""
        self.poutput("")
        return True


def main():
    DFSShell().cmdloop()


if __name__ == "__main__":
    main()
