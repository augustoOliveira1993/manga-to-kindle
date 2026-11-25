"""Contrato imutável de mangá."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid4

from manga_to_kindle.domain.chapter import Chapter
from manga_to_kindle.domain.errors import DomainValidationError


@dataclass(frozen=True, slots=True)
class Manga:
    title: str
    id: UUID = field(default_factory=uuid4)
    source_ref: str | None = None
    chapters: tuple[Chapter, ...] = ()
    author: str | None = None
    cover_path: Path | None = None
    language: str | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise DomainValidationError("O mangá precisa de um título.")
        if self.source_ref is not None and not self.source_ref.strip():
            raise DomainValidationError("A referência de origem não pode ser vazia.")
        if self.author is not None and not self.author.strip():
            raise DomainValidationError("O autor informado não pode ser vazio.")
        if self.language is not None and not self.language.strip():
            raise DomainValidationError("O idioma informado não pode ser vazio.")
        if self.cover_path is not None and not str(self.cover_path).strip():
            raise DomainValidationError("A capa local não pode ter um caminho vazio.")
        chapter_ids = [chapter.id for chapter in self.chapters]
        positions = [chapter.position for chapter in self.chapters]
        if len(chapter_ids) != len(set(chapter_ids)):
            raise DomainValidationError("Os capítulos do mangá precisam ter IDs únicos.")
        if len(positions) != len(set(positions)):
            raise DomainValidationError("A ordem dos capítulos do mangá não pode se repetir.")
        if any(chapter.manga_id != self.id for chapter in self.chapters):
            raise DomainValidationError("Cada capítulo precisa pertencer ao mangá informado.")
