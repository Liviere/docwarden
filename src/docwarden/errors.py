class DocwardenError(Exception):
    """Base class for docwarden errors."""


class ConfigError(DocwardenError):
    """Raised when [tool.docwarden] configuration is invalid or unreadable."""


class NotAGitRepositoryError(DocwardenError):
    """Raised when an operation requires a git work tree but none was found."""
