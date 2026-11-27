"""Domain models for device profiles and application resource preferences."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from manga_to_kindle.domain.errors import DomainValidationError
from manga_to_kindle.domain.image_processing import ReadingDirection

MIB = 1024 * 1024
GIB = 1024 * MIB

BASIC_8_PROFILE_ID = UUID("1f716073-6621-4ac2-a1c0-c1f2b1ec0808")
BASIC_10_PROFILE_ID = UUID("1f716073-6621-4ac2-a1c0-c1f2b1ec1010")
PAPERWHITE_10_PROFILE_ID = UUID("1f716073-6621-4ac2-a1c0-c1f2b1ec1011")


@dataclass(frozen=True, slots=True)
class DeviceProfileSettings:
    id: UUID
    name: str
    model: str
    generation: int | None
    width: int
    height: int
    ppi: int | None = None
    grayscale_levels: int = 16
    grayscale: bool = True
    direction: ReadingDirection = ReadingDirection.RIGHT_TO_LEFT
    margin_left: int = 0
    margin_top: int = 0
    margin_right: int = 0
    margin_bottom: int = 0
    crop_margins: bool = False
    quality: int = 90
    built_in: bool = False

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if (
            not normalized_name
            or len(normalized_name) > 128
            or normalized_name in {".", ".."}
            or any(character in normalized_name for character in '<>"|?*:/\\')
        ):
            raise DomainValidationError(
                "O nome do perfil está vazio ou contém caracteres inválidos."
            )
        if not self.model.strip():
            raise DomainValidationError("Informe o modelo ou destino deste perfil.")
        if self.generation is not None and (
            type(self.generation) is not int or not 1 <= self.generation <= 100
        ):
            raise DomainValidationError("A geração do dispositivo precisa ser um inteiro positivo.")
        if (
            type(self.width) is not int
            or type(self.height) is not int
            or not 1 <= self.width <= 10_000
            or not 1 <= self.height <= 10_000
            or self.width * self.height > 50_000_000
        ):
            raise DomainValidationError(
                "Cada dimensão precisa ficar entre 1 e 10.000 pixels e a área até 50 megapixels."
            )
        if self.ppi is not None and (type(self.ppi) is not int or not 1 <= self.ppi <= 1200):
            raise DomainValidationError("A densidade do perfil precisa ficar entre 1 e 1.200 ppi.")
        if type(self.grayscale_levels) is not int or not 2 <= self.grayscale_levels <= 256:
            raise DomainValidationError("Os níveis de cinza do perfil estão fora do intervalo.")
        if type(self.grayscale) is not bool or not self.grayscale:
            raise DomainValidationError(
                "O processamento de imagens disponível nesta versão produz saída "
                "em escala de cinza."
            )
        if type(self.crop_margins) is not bool or type(self.built_in) is not bool:
            raise DomainValidationError("As opções do perfil precisam usar valores booleanos.")
        margins = (self.margin_left, self.margin_top, self.margin_right, self.margin_bottom)
        if any(type(margin) is not int or not 0 <= margin <= 40 for margin in margins):
            raise DomainValidationError("Cada margem precisa ficar entre 0 e 40 pixels.")
        if self.margin_left + self.margin_right >= self.width:
            raise DomainValidationError("As margens horizontais excedem a área útil do perfil.")
        if self.margin_top + self.margin_bottom >= self.height:
            raise DomainValidationError("As margens verticais excedem a área útil do perfil.")
        if type(self.quality) is not int or not 1 <= self.quality <= 100:
            raise DomainValidationError("A qualidade precisa ficar entre 1 e 100.")
        if not isinstance(self.direction, ReadingDirection):
            raise DomainValidationError("A direção de leitura precisa ser RTL ou LTR.")
        object.__setattr__(self, "name", normalized_name)


FACTORY_DEVICE_PROFILES: tuple[DeviceProfileSettings, ...] = (
    DeviceProfileSettings(
        BASIC_8_PROFILE_ID,
        "Kindle Básico 8ª geração",
        "Kindle Básico",
        8,
        600,
        800,
        167,
        built_in=True,
    ),
    DeviceProfileSettings(
        BASIC_10_PROFILE_ID,
        "Kindle Básico 10ª geração",
        "Kindle Básico",
        10,
        600,
        800,
        167,
        built_in=True,
    ),
    DeviceProfileSettings(
        PAPERWHITE_10_PROFILE_ID,
        "Kindle Paperwhite 10ª geração",
        "Kindle Paperwhite",
        10,
        1072,
        1448,
        300,
        built_in=True,
    ),
)


@dataclass(frozen=True, slots=True)
class ApplicationPreferences:
    selected_profile_id: UUID = BASIC_10_PROFILE_ID
    download_concurrency: int = 2
    download_directory: Path | None = None
    export_directory: Path | None = None
    cache_directory: Path | None = None
    cache_limit_bytes: int = GIB
    cache_retention_days: int = 30

    def __post_init__(self) -> None:
        if not isinstance(self.selected_profile_id, UUID):
            raise DomainValidationError("O perfil de dispositivo selecionado é inválido.")
        if type(self.download_concurrency) is not int or not 1 <= self.download_concurrency <= 2:
            raise DomainValidationError("A concorrência de downloads precisa ser 1 ou 2.")
        if (
            type(self.cache_limit_bytes) is not int
            or not 100 * MIB <= self.cache_limit_bytes <= 20 * GIB
        ):
            raise DomainValidationError("O limite de cache precisa ficar entre 100 MiB e 20 GiB.")
        if (
            type(self.cache_retention_days) is not int
            or not 1 <= self.cache_retention_days <= 365
        ):
            raise DomainValidationError("A retenção do cache precisa ficar entre 1 e 365 dias.")
        names = ("download_directory", "export_directory", "cache_directory")
        normalized = tuple(
            _normalize_directory(path)
            for path in (
                self.download_directory,
                self.export_directory,
                self.cache_directory,
            )
            if path is not None
        )
        normalized_index = 0
        for name in names:
            path = getattr(self, name)
            if path is not None:
                object.__setattr__(self, name, normalized[normalized_index])
                normalized_index += 1
        for index, path in enumerate(normalized):
            for other in normalized[index + 1 :]:
                if path == other or path in other.parents or other in path.parents:
                    raise DomainValidationError(
                        "As pastas de downloads, exports e cache precisam ser independentes."
                    )


def factory_profile(profile_id: UUID) -> DeviceProfileSettings | None:
    return next((profile for profile in FACTORY_DEVICE_PROFILES if profile.id == profile_id), None)


def _normalize_directory(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise DomainValidationError("As pastas precisam usar caminhos absolutos.")
    if path.anchor.startswith("\\\\"):
        raise DomainValidationError("Pastas de rede não podem ser usadas como padrão.")
    current = path
    while True:
        if current.is_symlink():
            raise DomainValidationError("Pastas simbólicas não podem ser usadas como padrão.")
        if current.parent == current:
            break
        current = current.parent
    normalized = path.resolve(strict=False)
    if ".." in path.parts:
        raise DomainValidationError("O caminho da pasta não pode conter segmentos '..'.")
    return normalized
