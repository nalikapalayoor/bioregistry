"""Download registry information from N2T."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar

import yaml
from pystow.utils import download

from bioregistry.constants import RAW_DIRECTORY, URI_FORMAT_KEY
from bioregistry.external.alignment_utils import Aligner, load_processed

__all__ = [
    "N2TAligner",
    "get_n2t",
]

URL = "https://n2t.net/e/n2t_full_prefixes.yaml"
DIRECTORY = Path(__file__).parent.resolve()
RAW_PATH = RAW_DIRECTORY / "n2t.yml"
PROCESSED_PATH = DIRECTORY / "processed.json"
SKIP = {
    "zzztestprefix": "test prefix should not be considered",
    "urn": "too meta",
    "url": "too meta",
    "purl": "too meta",
    "lsid": "too meta",
    "hdl": "paid service, too meta",
    "repec": "irrelevant prefix from economics",
    "merops": "issue with miriam having duplicate prefixes for this resource",  # FIXME
    "hgnc.family": "issue with miriam having duplicate prefixes for this resource",  # FIXME
}
SKIP_URI_FORMATS = {
    "http://arabidopsis.org/servlets/TairObject?accession=$1",
}


def get_n2t(force_download: bool = False) -> dict[str, dict[str, Any]]:
    """Get the N2T registry."""
    if PROCESSED_PATH.exists() and not force_download:
        return load_processed(PROCESSED_PATH)

    download(url=URL, path=RAW_PATH, force=True)
    # they give malformed YAML so time to write a new parser
    with RAW_PATH.open() as file:
        data = yaml.safe_load(file)

    rv = {
        key: _process(record)
        for key, record in data.items()
        if record["type"] == "scheme" and "/" not in key and key not in SKIP
    }

    with PROCESSED_PATH.open("w") as file:
        json.dump(rv, file, sort_keys=True, indent=2)
    return rv


def _process(record: dict[str, Any]) -> dict[str, Any]:
    rv = {
        "name": record.get("name"),
        URI_FORMAT_KEY: _get_uri_format(record),
        "description": record.get("description"),
        "homepage": record.get("more"),
        "pattern": record.get("pattern"),
        "example": record.get("test"),
        "namespaceEmbeddedInLui": (record.get("prefixed") == "true"),
    }
    return {k: v for k, v in rv.items() if v is not None}


def _get_uri_format(record: dict[str, Any]) -> str | None:
    raw_redirect: str | None = record.get("redirect")
    if raw_redirect is None:
        return None
    uri_format = raw_redirect.replace("$id", "$1")
    if uri_format in SKIP_URI_FORMATS:
        return None
    return uri_format


class N2TAligner(Aligner):
    """Aligner for the N2T."""

    key = "n2t"
    getter = get_n2t
    curation_header: ClassVar[Sequence[str]] = ("name", "homepage", "description")

    def get_skip(self) -> Mapping[str, str]:
        """Get the prefixes in N2T that should be skipped."""
        return SKIP


if __name__ == "__main__":
    N2TAligner.cli()
