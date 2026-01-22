"""Base class for component-specific presets."""


class BasePresets:
    """Base class for organizing component-specific mock presets."""

    @classmethod
    def get_all(cls) -> dict:
        """Get all presets as a dictionary."""
        return {
            name: getattr(cls, name)
            for name in dir(cls)
            if not name.startswith("_") and name.isupper()
        }
