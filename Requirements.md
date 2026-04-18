# Requirements

## Overview

In this project, you will extend a provided Chord-based distributed hash table into a **Distributed File System (DFS)**. Your DFS must support:

### Part 1

1. **Distributed file storage** using Chord lookups
2. **Page-based file metadata management**
3. **Distributed sorting of file contents**

Chord assigns each key to the node responsible for its successor on the identifier ring, and uses finger tables to achieve logarithmic routing. Replication improves reliability and performance, but introduces consistency challenges. Paxos addresses the fault-tolerance side by ensuring that replicas execute operations in the same order despite crashes and lost or delayed messages.

---

## Learning Objectives

By completing this project, students will be able to:

* extend a DHT into an application-level distributed storage system,
* represent files as distributed metadata plus distributed pages,
* route storage and retrieval operations through Chord,
* design a distributed sorting workflow over partitioned file pages,
* explain why replication requires consistency control,
* implement a simplified Paxos protocol for replicated DFS updates,
* evaluate behavior under node failure and message delay/loss assumptions.

---

## 3. Functional Requirements

# Part A — DFS Layer on Top of Chord

Build a DFS abstraction over the provided Chord system.

## Required DFS operations

Implement at least the following API:

```text
touch(filename)
append(filename, local_path)
read(filename)
head(filename, n)
tail(filename, n)
delete_file(filename)
ls()
stat(filename)
```

## Required behavior

A distributed file is represented as:

* **Metadata object**

  * logical filename
  * total number of pages
  * file size
  * ordered list of page descriptors
* **Page objects**

  * each page stores a chunk of the file content
  * each page is stored in the Chord ring using a hash-derived key

### Simplified Data Model

Example metadata JSON:

```json
{
  "filename": "music.json",
  "size_bytes": 40960,
  "num_pages": 3,
  "pages": [
    {"page_no": 0, "guid": "g1", "replicas": ["r1","r2","r3"]},
    {"page_no": 1, "guid": "g2", "replicas": ["r4","r5","r6"]},
    {"page_no": 2, "guid": "g3", "replicas": ["r7","r8","r9"]}
  ],
  "version": 12
}
```

Example sorted-record page format:

```text
0012,alice
0042,bob
0190,carol
```

## Chord + DFS Basics

Implement:

* file metadata
* page storage
* `touch`, `append`, `read`, `ls`, `stat`

Your notes describe exactly this DFS structure: metadata stores the logical file name, size, and page GUIDs, while page content is distributed across peers.

### Metadata placement

Store metadata deterministically in the DHT, for example:

```text
metadata_key = hash("metadata:" + filename)
```

### Page placement

Store each appended page with a deterministic page key such as:

```text
page_key = hash(filename + ":" + page_number)
```

The key must be routed to the node responsible for its Chord successor.

---

# Part B — Distributed Sort

Implement:

```text
sort_file(filename, output_filename)
```

Assume the input distributed file contains records of the form:

```text
key,value
```

where `key` is sortable.

## Required distributed sorting model

You must implement a distributed sorting workflow consistent with the provided notes:

1. Read each page of the input file
2. Parse each record `(key, value)`
3. Route each record to the peer responsible for the successor of `hash(key)` or `key` itself, depending on your chosen design
4. At each responsible peer, insert incoming records into a local ordered structure

   * e.g. sorted list, balanced BST abstraction, heap followed by final sort, etc.
5. Produce a globally sorted output file
6. Store the sorted output as a new distributed file in the DFS

Your P2P notes explicitly describe distributed sorting by routing each record to the closest successor of the key, then maintaining sorted content locally at the responsible peer.

## Minimum correctness requirement

The final `output_filename` must contain all records from `filename` in globally sorted order.

## Minimum design requirement

You must include a short write-up describing:

* how records are partitioned across peers,
* how local sorted state is maintained,
* how the final sorted distributed file is assembled.

### Distributed Sort

Implement:

* page scanning
* routing records by key
* local sorted aggregation
* output assembly and validation

---

## Required protocol concepts

Your solution must include:

* a **leader**
* **proposal/sequence number** or ballot number
* **ACCEPT** messages
* **LEARN** messages
* majority-based commitment with at least 3 replicas

## Simplified rule for this assignment

For each replicated DFS update:

1. Leader proposes operation `o`
2. Replicas receive `ACCEPT(o, t)`
3. Replicas respond with `LEARN(o, t)`
4. Operation is committed once a majority has learned it
5. All replicas apply committed operations in the same order

This reflects the course’s emphasis that replicated servers must execute operations in the same order, and that three servers are needed so a majority can confirm a learned operation even under a crash.

---

## Test evidence

Provide:

* sample input files
* sorted output file
* screenshots or logs of Paxos messages
* correctness checks

---

## Deliverables

Submit the following on Canvas:

### A. Source code

A complete runnable project.

### B. README

### C. Design report (3–5 pages)

Address:

* Chord integration
* metadata and page design
* distributed sorting strategy
* replication strategy
* Paxos message flow
* failure assumptions
* limitations and future improvements

---

## Hints

* Start with metadata replication before page replication.
* Use deterministic keys everywhere.
* Keep Paxos logs human-readable.
* Separate “Chord routing correctness” from “DFS correctness.”
* Validate sorting with a local checker:

  * read all output records,
  * assert nondecreasing key order.
* Add a version number to metadata.
* For debugging, log:

  * node ID,
  * successor,
  * predecessor,
  * file/page GUID,
  * Paxos proposal number.

---

## Fault model

Assume:

* crash failures only
* no Byzantine behavior
* messages may be delayed, lost, duplicated, or reordered
* corrupted messages may be discarded
* deterministic operations

These assumptions are directly aligned with the Chapter 8 material.

---

## Implementation Constraints

## Communication

You may use:

* sockets
* RPC-style messaging, e.g. Pyro
* ZeroMQ
* another instructor-approved mechanism

## Persistence

At minimum, store enough local state to:

* reconstruct node-owned data while the program is running,
* inspect metadata/pages for debugging.

Durable disk recovery is optional unless you choose to implement it.

## Concurrency

You may use:

* threads,
* async I/O,
* multiprocessing,
* or a simpler event-driven design.

## Minimum topology

At least **5 Chord peers** and **3 Paxos replicas** per replicated DFS object or metadata group.

---

## Suggested Architecture

One reasonable architecture is:

```text
+----------------------+
| DFS Client CLI       |
+----------------------+
          |
          v
+----------------------+
| DFS API              |
| touch/append/read    |
| sort_file/delete     |
+----------------------+
          |
          v
+----------------------+
| Replication Layer    |
| Paxos leader/follower|
+----------------------+
          |
          v
+----------------------+
| Chord Routing Layer  |
| locateSuccessor()    |
| put/get/delete       |
+----------------------+
          |
          v
+----------------------+
| Local Storage        |
| metadata/pages/log   |
+----------------------+
```

This decomposition is a good fit for the course’s layered view of distributed systems and middleware.
