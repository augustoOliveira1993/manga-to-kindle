"""Erros independentes de UI e persistência do domínio."""


class DomainValidationError(ValueError):
    """Uma entidade recebeu dados que violam suas invariantes."""

    code = "DOMAIN_INVARIANT_VIOLATION"
