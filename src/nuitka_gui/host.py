"""What this machine can tell us about itself.

Every answer here has a fallback, because a build has to be able to start
even when the machine will not say how much RAM it has or how many cores it
runs. The numbers only pick a default thread count; they are never required.
"""

import ctypes
import os
from pathlib import Path

# One cl.exe holds roughly this much working set. Nuitka's default of one job
# per core ignores that and can exhaust a smaller machine, so the default here
# is capped by RAM as well as by cores.
_GB_PER_JOB = 0.9


class _MemoryStatus(ctypes.Structure):
    """The shape ``GlobalMemoryStatusEx`` writes into."""

    _fields_ = [
        ("length", ctypes.c_ulong),
        ("memory_load", ctypes.c_ulong),
        ("total_phys", ctypes.c_ulonglong),
        ("avail_phys", ctypes.c_ulonglong),
        ("total_page_file", ctypes.c_ulonglong),
        ("avail_page_file", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("avail_virtual", ctypes.c_ulonglong),
        ("avail_extended_virtual", ctypes.c_ulonglong),
    ]


def launch_dir() -> Path:
    """The folder the app was started from, or the home folder."""
    try:
        return Path.cwd()
    except OSError:
        return Path.home()


def physical_gb() -> float:
    """Total physical RAM in GB, or 0.0 when it cannot be determined."""
    if not hasattr(ctypes, "windll"):
        return 0.0
    status = _MemoryStatus()
    status.length = ctypes.sizeof(_MemoryStatus)
    try:
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    except (AttributeError, OSError):
        return 0.0
    return status.total_phys / 1024**3 if ok else 0.0


def logical_cores() -> int:
    """Logical core count, or 1 when the machine will not say."""
    return os.cpu_count() or 1


def default_jobs() -> int:
    """How many C compiler processes this machine's RAM can take.

    Budgets about 0.9 GB per cl.exe, then caps that by the core count so a
    large machine is not offered more jobs than it has cores.
    """
    cores = logical_cores()
    gigs = physical_gb()
    if gigs <= 0:
        return max(1, cores // 2)
    return max(1, min(cores, int(gigs / _GB_PER_JOB)))
