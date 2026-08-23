from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

__version__: str
try:
    __version__ = _pkg_version("migrator-gen")
except PackageNotFoundError:
    __version__ = "1.0.1"

VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH = (int(x) for x in __version__.split(".")[:3])
VERSION_TRIPLE: str = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"
SDK_NAME: str = "migrator-gen"
USER_AGENT: str = f"migrator-gen-sdk/{__version__}"
