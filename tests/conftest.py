import sys
from pathlib import Path


def _prepend_repo_root_to_sys_path() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    repo_root_str = str(repo_root)
    if repo_root_str in sys.path:
        sys.path.remove(repo_root_str)
    sys.path.insert(0, repo_root_str)


_prepend_repo_root_to_sys_path()
