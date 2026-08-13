from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("docwarden")
except PackageNotFoundError:  # pragma: no cover - running from source without install
    __version__ = "0.0.0+unknown"
