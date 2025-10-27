"""Built-in plugins for the advanced codebase analyzer."""

from .ci_config import ContinuousIntegrationPlugin
from .dependency_health import DependencyHealthPlugin
from .git_metadata import GitMetadataPlugin
from .large_files import LargeFilePlugin
from .license_inventory import LicenseInventoryPlugin

__all__ = [
    "ContinuousIntegrationPlugin",
    "DependencyHealthPlugin",
    "GitMetadataPlugin",
    "LargeFilePlugin",
    "LicenseInventoryPlugin",
]

