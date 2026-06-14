"""Sync AKShare reference documents and build compact interface indexes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from typing import TypedDict

DOCUMENT_URLS = {
    "article": "https://akshare.akfamily.xyz/_sources/data/article/article.md.txt",
    "bank": "https://akshare.akfamily.xyz/_sources/data/bank/bank.md.txt",
    "bond": "https://akshare.akfamily.xyz/_sources/data/bond/bond.md.txt",
    "currency": "https://akshare.akfamily.xyz/_sources/data/currency/currency.md.txt",
    "dc": "https://akshare.akfamily.xyz/_sources/data/dc/dc.md.txt",
    "energy": "https://akshare.akfamily.xyz/_sources/data/energy/energy.md.txt",
    "fund_public": "https://akshare.akfamily.xyz/_sources/data/fund/fund_public.md.txt",
    "fund_private": "https://akshare.akfamily.xyz/_sources/data/fund/fund_private.md.txt",
    "futures": "https://akshare.akfamily.xyz/_sources/data/futures/futures.md.txt",
    "fx": "https://akshare.akfamily.xyz/_sources/data/fx/fx.md.txt",
    "hf": "https://akshare.akfamily.xyz/_sources/data/hf/hf.md.txt",
    "index": "https://akshare.akfamily.xyz/_sources/data/index/index.md.txt",
    "interest_rate": (
        "https://akshare.akfamily.xyz/_sources/data/interest_rate/interest_rate.md.txt"
    ),
    "macro": "https://akshare.akfamily.xyz/_sources/data/macro/macro.md.txt",
    "nlp": "https://akshare.akfamily.xyz/_sources/data/nlp/nlp.md.txt",
    "option": "https://akshare.akfamily.xyz/_sources/data/option/option.md.txt",
    "others": "https://akshare.akfamily.xyz/_sources/data/others/others.md.txt",
    "qdii": "https://akshare.akfamily.xyz/_sources/data/qdii/qdii.md.txt",
    "qhkc": "https://akshare.akfamily.xyz/_sources/data/qhkc/index.rst.txt",
    "qhkc_broker": "https://akshare.akfamily.xyz/_sources/data/qhkc/broker.md.txt",
    "qhkc_commodity": "https://akshare.akfamily.xyz/_sources/data/qhkc/commodity.md.txt",
    "qhkc_fund": "https://akshare.akfamily.xyz/_sources/data/qhkc/fund.md.txt",
    "qhkc_fundamental": (
        "https://akshare.akfamily.xyz/_sources/data/qhkc/fundamental.md.txt"
    ),
    "qhkc_index_data": (
        "https://akshare.akfamily.xyz/_sources/data/qhkc/index_data.md.txt"
    ),
    "qhkc_tools": "https://akshare.akfamily.xyz/_sources/data/qhkc/tools.md.txt",
    "spot": "https://akshare.akfamily.xyz/_sources/data/spot/spot.md.txt",
    "stock": "https://akshare.akfamily.xyz/_sources/data/stock/stock.md.txt",
    "tool": "https://akshare.akfamily.xyz/_sources/data/tool/tool.md.txt",
    "event": "https://akshare.akfamily.xyz/_sources/data/event/event.md.txt",
}

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FIELD_PATTERN = re.compile(r"^(接口|目标地址|描述|限量)[:：]\s*(.*?)\s*$")


class InterfaceEntry(TypedDict, total=False):
    """A searchable AKShare interface summary."""

    interface: str
    section: list[str]
    line: int
    target_url: str
    description: str
    limit: str


def parse_interfaces(text: str) -> list[InterfaceEntry]:
    """Extract interface metadata and heading context from an AKShare document."""

    headings: dict[int, str] = {}
    entries: list[InterfaceEntry] = []
    current: InterfaceEntry | None = None
    pending_field: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if pending_field is not None and line:
            if pending_field == "interface":
                current = {
                    "interface": line,
                    "section": [headings[level] for level in sorted(headings)],
                    "line": line_number,
                }
                entries.append(current)
            elif current is not None:
                current["description"] = line
            pending_field = None
            continue

        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            heading = heading_match.group(2)
            if heading == "接口名称":
                pending_field = "interface"
                continue
            if heading == "接口描述":
                pending_field = "description"
                continue
            headings[level] = heading
            headings = {
                heading_level: title
                for heading_level, title in headings.items()
                if heading_level <= level
            }
            continue

        field_match = FIELD_PATTERN.match(line)
        if not field_match:
            continue

        field, value = field_match.groups()
        if field == "接口":
            current = {
                "interface": value,
                "section": [headings[level] for level in sorted(headings)],
                "line": line_number,
            }
            entries.append(current)
        elif current is not None:
            key = {
                "目标地址": "target_url",
                "描述": "description",
                "限量": "limit",
            }[field]
            current[key] = value

    return entries


def write_document(
    name: str, text: str, output_directory: Path, source_url: str
) -> tuple[Path, Path]:
    """Write one raw document and its generated interface index."""

    raw_directory = output_directory / "raw"
    index_directory = output_directory / "index"
    raw_directory.mkdir(parents=True, exist_ok=True)
    index_directory.mkdir(parents=True, exist_ok=True)

    raw_path = raw_directory / f"{name}.md"
    index_path = index_directory / f"{name}.json"
    raw_path.write_text(text, encoding="utf-8")

    payload = {
        "schema_version": 1,
        "document": name,
        "source_url": source_url,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "interfaces": parse_interfaces(text),
    }
    index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return raw_path, index_path


def download_document(url: str) -> str:
    """Download a UTF-8 AKShare source document."""

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "QuantAI-AKShare-doc-sync/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def sync_documents(
    names: list[str], output_directory: Path, source_directory: Path | None = None
) -> None:
    """Sync selected documents from local files or official AKShare URLs."""

    for name in names:
        source_url = DOCUMENT_URLS[name]
        if source_directory is None:
            text = download_document(source_url)
        else:
            source_filename = source_url.rsplit("/", maxsplit=1)[-1]
            source_path = source_directory / source_filename
            text = source_path.read_text(encoding="utf-8")
        raw_path, index_path = write_document(name, text, output_directory, source_url)
        print(f"{name}: wrote {raw_path} and {index_path}")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--documents",
        nargs="+",
        choices=sorted(DOCUMENT_URLS),
        default=sorted(DOCUMENT_URLS),
        help="Documents to sync (default: all).",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("docs/akshare"),
        help="Destination directory (default: docs/akshare).",
    )
    parser.add_argument(
        "--source-directory",
        type=Path,
        help="Import NAME.md.txt files locally instead of downloading them.",
    )
    return parser


def main() -> None:
    """Run the AKShare documentation sync."""

    args = build_parser().parse_args()
    if args.output_directory.exists() and not args.output_directory.is_dir():
        raise NotADirectoryError(args.output_directory)
    sync_documents(args.documents, args.output_directory, args.source_directory)


if __name__ == "__main__":
    main()
