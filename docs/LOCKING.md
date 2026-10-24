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
