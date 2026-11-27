"""Casos de uso e coordenação local de atualizações F010."""

from manga_to_kindle.application.updates.preferences import SaveUpdatePreference
from manga_to_kindle.application.updates.refresh_manga_catalog import (
    RefreshMangaCatalog,
    RefreshMangaCatalogResult,
    UpdateTrigger,
)
from manga_to_kindle.application.updates.scheduler import (
    PeriodicUpdateScheduler,
    ScheduledUpdate,
)

__all__ = [
    "PeriodicUpdateScheduler",
    "RefreshMangaCatalog",
    "RefreshMangaCatalogResult",
    "SaveUpdatePreference",
    "ScheduledUpdate",
    "UpdateTrigger",
]
