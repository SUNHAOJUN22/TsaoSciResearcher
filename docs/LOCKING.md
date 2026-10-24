# Lock ownership and recovery

`tsao_researcher.io.exclusive_lock` records a random ownership token, a PID,
the hostname and creation time. Releasing a lock requires the original process,
file identity and ownership token. A forked child cannot remove its parent's
lock. Age alone does not authorize recovery of a live owner's lock.

Stale recovery requires evidence that a local owner has exited. On POSIX, a
zero signal queries process existence. On Windows, the runtime opens a process
handle with query and synchronization rights, checks its PID, and performs a
zero-duration wait. It always attempts to close an acquired handle. A signaled
process handle or a confirmed absent PID permits recovery after `stale_after`.
Access denial, identity mismatch and query failures keep the lock occupied.
PID reuse can conservatively delay recovery; the runtime never terminates a
process to obtain a lock.

Stale-owner checks and pathname removal are serialized by a persistent hidden
recovery guard in the lock directory. The guard uses `fcntl.flock` on POSIX and
`msvcrt.locking` on Windows, with a process-local mutex for concurrent threads.
It is deliberately not deleted: unlinking a locked guard could let waiters lock
different inodes. Capsule export excludes this reserved runtime file so its
presence does not become research input or alter exported provenance. On POSIX,
fork waits for active stale recovery to finish; the child resets the inherited
thread mutex before it can attempt recovery. This coordinates the lock helper;
it does not make general-purpose `fork()` from a multithreaded process safe.
If the platform temporarily denies unlink of a stale lock, recovery retries
without removing or bypassing the lock and remains bounded by the acquisition
deadline.
Owner payload probes and owner cleanup use the same guard, preventing a Windows
reader handle from racing the owner's pathname removal.
Owner cleanup waits for the guard only up to `DEFAULT_LOCK_TIMEOUT`. If that
deadline expires, it leaves the lock file in place rather than unlinking without
synchronization; contenders may keep timing out while the owner process remains
alive, and stale recovery can proceed after that process exits.

Windows `os.kill(pid, 0)` is not a POSIX existence query: CPython console builds
route zero to `GenerateConsoleCtrlEvent`. The Windows implementation therefore
uses process-handle observation. Waiting on the handle also distinguishes an
exited process whose exit code happens to be `STILL_ACTIVE` (259).

Unreadable, malformed or foreign-host ownership remains protected. These files
can cause `LockTimeoutError` even when old; their age does not establish who is
using them. Recovery of uncertain metadata requires an operator to establish
that all relevant writers have stopped. This preserves the ownership policy
introduced by the process-safety update. Older age-only writers do not enforce
that policy and must be stopped before a coordinated upgrade.

The hostname check is a conservative local-process boundary, not a distributed
lock service or a guarantee about shared-hostname and synchronized filesystems.

Both compatibility workflows use Bash's failure propagation for their native
commands, including on Windows. A failed test command stops the step, so a later
successful command cannot conceal the failure. The lock-process, owner-query
and catalog-cache regressions run explicitly in the Windows/Linux matrices.

## Implementation references

- [CPython 3.12 Windows `os.kill` implementation](https://github.com/python/cpython/blob/v3.12.10/Modules/posixmodule.c)
- [GenerateConsoleCtrlEvent](https://learn.microsoft.com/en-us/windows/console/generateconsolectrlevent)
- [OpenProcess](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess)
- [GetProcessId](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getprocessid)
- [WaitForSingleObject](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject)
- [Python 3.12 `os.register_at_fork`](https://docs.python.org/3.12/library/os.html#os.register_at_fork)
- [Python 3.12 `fcntl.flock`](https://docs.python.org/3.12/library/fcntl.html#fcntl.flock)
- [Python 3.12 `msvcrt.locking`](https://docs.python.org/3.12/library/msvcrt.html#msvcrt.locking)
- [Python 3.12 Windows behavior for `os.remove`/`os.unlink`](https://docs.python.org/3.12/library/os.html#os.remove)
- [Python 3.12 Windows open-handle sharing and `PermissionError`](https://docs.python.org/3.12/library/tempfile.html#tempfile.NamedTemporaryFile)
- [Microsoft CRT file-sharing modes](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/sopen-s-wsopen-s)
