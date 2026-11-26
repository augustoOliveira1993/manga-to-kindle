"""Leitura limitada em blocos para origens de imagens locais e arquivos compactados."""

from __future__ import annotations

from typing import Protocol

_READ_CHUNK_SIZE = 64 * 1024


class ReadableBinary(Protocol):
    def read(self, size: int = -1) -> bytes: ...


def read_bounded(stream: ReadableBinary, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(min(_READ_CHUNK_SIZE, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            break
    return b"".join(chunks)
