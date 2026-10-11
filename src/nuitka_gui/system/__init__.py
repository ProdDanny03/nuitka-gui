"""What the machine can tell the window about itself, and what it can find."""

from nuitka_gui.system.host import (
    default_jobs,
    launch_dir,
    logical_cores,
    physical_gb,
)
from nuitka_gui.system.sources import (
    default_output,
    find_main,
    main_roots,
)

__all__ = [
    'default_jobs',
    'default_output',
    'find_main',
    'launch_dir',
    'logical_cores',
    'main_roots',
    'physical_gb',
]
