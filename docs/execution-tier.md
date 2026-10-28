# The execution tier: a workstation harness and a clone swarm

The system runs as two tiers. The **head** is a cloud agent — a hosted
model — and it holds all judgment: calibration, doctrine adjudication,
every gate that can commit resources. The **execution tier** is a single
consumer workstation on the same LAN — a mid-range desktop with a
last-generation GPU — running a local inference server and a small VM
fleet. Curiosity is cheap on the local tier; judgment stays expensive.
The local tier is a convenience, never a dependency: if the workstation
goes dark, the system degrades to the head alone and notices nothing
structural.

Three mechanisms make an unmanaged home workstation safe to build on:
leases with wake-on-demand, an activity-aware sleep decider, and a
hash-pinned clone swarm.

## 1. Reference-counted wake leases

Workers never touch the workstation directly. They take a **lease**:

```
lease.sh acquire <worker-id> [--wake]
lease.sh release <worker-id>
lease.sh list | count | probe
```

- A lease is a file in a state directory; the count of live files is the
  reference count. Leases older than a TTL are pruned as crashed-worker
  safety.
- `acquire --wake` probes the host over SSH. If it is asleep, the harness
  fires a wake request through a LAN wake relay (a phone on the home
  network that emits the Wake-on-LAN packet — it refuses to fire from any
  other network), then waits for SSH before handing the lease out. A
  failed wake is a clean exit code, and callers degrade to CPU fallbacks;
  nothing retries blindly inside a cycle.
- The **last release** runs the sleep decider (below). Intermediate
  releases only decrement.

## 2. The sleep decider, and the bridge that fixed it

The workstation should sleep whenever nobody — human or agent — is using
it. Two independent systems guard that decision, and the seam between
them is the interesting part:

- The **VM-side decider** runs at last-release: sleep only if no leases
  remain, no wake flag is fresh, and the interactive session has been
  idle past a threshold. A human at the keyboard is never slept on.
- An **on-host overnight check** runs on a repeating trigger with the
  same rule in local form: it reads a *wake-need flag file* on the host,
  an idle probe written by a resident in-session task (real input idle,
  measured in the interactive session — not inferred from lock state),
  and an audio-activity signal: media playback counts as activity,
  because the input-idle timer ignores it and a machine playing music is
  a machine in use.

**The failure this design had to learn:** the on-host check is
*lease-blind*. It cannot see the lease registry, which lives on the
controller. A wake acquired over the relay made the machine available;
seven minutes later the on-host check found no fresh flag file, a long
idle timer, and no audio — and suspended the machine with two leases
held. Two stay-awake systems, each correct in isolation, composed into a
fault because they shared no signal.

**The bridge:** the lease manager now speaks the on-host check's own
language. Every successful `acquire` also stamps the flag file on the
host with the current date (the check treats a date-stamped flag as
"a worker asked" for the rest of the day); the last release clears the
stamp — but only when the file's content matches the stamp format, so a
flag a human wrote by hand is never deleted — before running the
decider. Both operations are best-effort and logged; a failed stamp logs
a warning rather than failing the lease, because the one unacceptable
outcome is a *silent* desync between the two systems.

Rules the seam taught:

- Every pair of independent stay-awake (or stay-asleep) mechanisms needs
  an explicit bridge signal. "Both check similar conditions" is not a
  bridge.
- Instrument the boundary, not just the components: the power log records
  every lease, stamp, clear, and verdict, which is what made the fault
  attributable to one named component in one read of the OS event log
  (sleep reason: application API, one named task, one timestamp).
- A liveness check that can pass while the thing is dead is decoration.
  Every probe in the harness is adversarially checked against a second
  signal (process present *and* fresh output).

## 3. The clone swarm

**Edition note:** the launcher, clone, and merge tooling described in
this section runs in the private deployment and is not part of this
public edition. The lease manager (`harness/lease.sh`, §1–2) is the
shipped half of the harness story; this section is the design record
for the other half.

For embarrassingly parallel collection work — the reference deployment
runs a recurring liquidity census over a market universe — the
workstation hosts a **swarm** of cloned VMs:

- **Golden base.** One maintained base image. Its disk hash, the
  launcher script's hash, and the template snapshot are pinned. The
  launcher refuses to run if any pin mismatches — a swarm that launches
  from unverified bits is not a swarm, it's a rumor.
- **Linked clones, capped.** Workers are copy-on-write clones of the
  golden base, at most 4 concurrent, each gated per-launch by a
  free-space check (at least the larger of a fixed floor and twice the
  template size). A pause file in a known location is a literal kill
  switch: present, nothing launches. The count is a property of the
  reference host and its roommate rule, not of the design: the launcher
  takes its worker count from the host it runs on, and a larger host —
  or several hosts under the same launcher — scales the fleet until
  the upstream API becomes the ceiling.
- **Hash-verified merge.** Each worker computes a SHA-256 of its output
  block *inside the guest*; the controller pulls the blocks and verifies
  each hash before merging. A block that fails verification fails the
  run, loudly.
- **The census pipeline.** Enumeration partitions the universe by time
  windows (the upstream API rejects deep pagination, so windows split
  recursively until each is under the page ceiling; a split floor of
  minutes and a depth cap bound the recursion — and the handful of
  buckets that still overflow are single mass-expiry instants, named in
  the report rather than silently truncated). Collection applies a
  lifetime-volume floor: thin items are counted in every summary but not
  fetched, and within a worker the fetch list is volume-sorted so a
  per-worker cap cuts the thinnest items first. Every run diffs against
  the previous one: appeared, vanished, common, and the largest single
  spread change.
- **The roommate rule.** The workstation is a person's machine first.
  Interactive use preempts the swarm instantly and without argument; the
  fleet yields, the run is discarded, and nobody files a ticket.

## 4. What the tiers owe each other

- The head never sends the local tier work whose output it cannot
  verify: extraction, triage, compression, soak tests — bounded,
  mechanical, source-checkable.
- The local tier never holds authority: no credentials, no gates, no
  commit path. If it vanished mid-run, the correct outcome is a slower
  cycle, not a wrong one.
- Bulk data moves between the controller and the workstation through an
  encrypted relay on commodity cloud storage when the direct path is the
  bottleneck — measured, not assumed: the relay leg ran an order of
  magnitude faster than the direct peer-to-peer leg on the same link.
