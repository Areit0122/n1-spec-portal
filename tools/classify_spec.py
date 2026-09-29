#!/usr/bin/env python3
"""Extract clause headings and message IE tables from 3GPP DOCX sources."""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "spec-source"
OUTPUT = ROOT / "docs" / "spec"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
MAX_DOCX_BYTES = 100 * 1024 * 1024
HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*(?:[AB])?)(.*)$")
MESSAGE = re.compile(r"\b(message|request|accept|complete|reject|command|response|notification)\b", re.I)


def cell_text(cell: ET.Element) -> str:
    return " ".join(element_text(cell).split())


def element_text(element: ET.Element) -> str:
    parts = []
    for node in element.iter():
        if node.tag == f"{{{NS['w']}}}t":
            parts.append(node.text or "")
        elif node.tag in (f"{{{NS['w']}}}tab", f"{{{NS['w']}}}br"):
            parts.append(" ")
    return "".join(parts)


def rows(table: ET.Element) -> list[list[str]]:
    return [[cell_text(c) for c in row.findall("w:tc", NS)] for row in table.findall("w:tr", NS)]


def docx_blocks(data: bytes):
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as archive:
        xml = ET.fromstring(archive.read("word/document.xml"))
    body = xml.find("w:body", NS)
    if body is None:
        return
    for item in body:
        if item.tag.endswith("}p"):
            text = " ".join(element_text(item).split())
            if text:
                style = item.find("w:pPr/w:pStyle", NS)
                yield ("p", text, style.get(f"{{{NS['w']}}}val", "") if style is not None else "")
        elif item.tag.endswith("}tbl"):
            yield ("table", rows(item), "")


def sources(version_dir: Path):
    for path in sorted(version_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() == ".docx":
            if path.stat().st_size > MAX_DOCX_BYTES:
                raise ValueError(f"DOCX exceeds {MAX_DOCX_BYTES} byte limit: {path}")
            yield path.name, path.read_bytes()
        elif path.is_file() and path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path) as archive:
                    for name in sorted(archive.namelist()):
                        if name.lower().endswith(".docx") and not name.startswith(("/", "\\")) and ".." not in Path(name).parts:
                            if archive.getinfo(name).file_size > MAX_DOCX_BYTES:
                                raise ValueError(f"DOCX exceeds {MAX_DOCX_BYTES} byte limit: {path}:{name}")
                            yield f"{path.name}:{name}", archive.read(name)
            except zipfile.BadZipFile as exc:
                raise ValueError(f"Invalid ZIP: {path}") from exc


def md(value: str) -> str:
    return (value.replace("&", "&amp;").replace("{", "&#123;").replace("}", "&#125;")
            .replace("<", "&lt;").replace(">", "&gt;")
            .replace("|", "\\|").replace("\n", " ").strip())


def classify(spec: str, version: str, path: str, data: bytes) -> str:
    out = [f"# TS {spec} — {version}", "", f"Source: `{md(path)}`", ""]
    current_clause = "Specification content"
    current_message = ""
    clause_count = message_count = ie_count = 0
    for kind, content, style in docx_blocks(data):
        if kind == "p":
            if style.upper().startswith("TOC"):
                continue
            if style.lower().startswith("heading"):
                match = HEADING.match(content)
                if match:
                    number, title = match.groups()
                    title = title.strip()
                    current_clause = f"{number} {title}".strip()
                    depth_match = re.search(r"\d+", style)
                    depth = min(int(depth_match.group()) + 1, 6) if depth_match else 2
                    message_root = bool(
                        re.fullmatch(r"8\.[23]\.\d+[AB]?", number)
                        if spec == "24.501"
                        else re.fullmatch(r"9\.\d+\.\d+[AB]?", number)
                    )
                    if message_root and MESSAGE.search(title):
                        current_message = current_clause
                    elif not (number.startswith(("8.2.", "8.3.")) if spec == "24.501" else number.startswith("9.")):
                        current_message = ""
                    clause_count += 1
                    if current_message:
                        message_count += 1
                    out.extend(["", f"{'#' * depth} {md(current_clause)}"])
                else:
                    current_message = ""
                    out.extend(["", f"## {md(content)}"])
            else:
                out.extend(["", md(content)])
            continue

        table = content
        if not table:
            continue
        header_index = next((i for i, row in enumerate(table[:4]) if any("presence" in x.lower() for x in row) and any("length" in x.lower() for x in row)), None)
        if header_index is not None:
            headers = table[header_index]
            table_title = current_message or current_clause
            out.extend(["", f"#### Message IE table — {md(table_title)}", ""])
            out.append("| " + " | ".join(md(x) or "—" for x in headers) + " |")
            out.append("| " + " | ".join("---" for _ in headers) + " |")
            for row in table[header_index + 1:]:
                if any(row):
                    padded = row + [""] * max(0, len(headers) - len(row))
                    out.append("| " + " | ".join(md(x) or "—" for x in padded[:len(headers)]) + " |")
                    ie_count += 1
        else:
            out.extend(["", "| " + " | ".join(md(c) or "—" for c in table[0]) + " |", "| " + " | ".join("---" for _ in table[0]) + " |"])
            out.extend("| " + " | ".join(md(c) or "—" for c in row[:len(table[0])]) + " |" for row in table[1:] if any(row))
    out.extend(["", "---", f"Extracted {clause_count} clause headings, {message_count} message/table sections, {ie_count} IE rows.", ""])
    return "\n".join(out)


def main() -> int:
    specs = []
    # ponytail: rebuild this generated-only subtree so removed input versions vanish on the next run.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    if SOURCE_ROOT.exists():
        for spec_dir in sorted(p for p in SOURCE_ROOT.iterdir() if p.is_dir()):
            spec_versions = []
            for version_dir in sorted(p for p in spec_dir.iterdir() if p.is_dir()):
                files = list(sources(version_dir))
                if not files:
                    continue
                page_dir = OUTPUT / spec_dir.name / version_dir.name
                page_dir.mkdir(parents=True, exist_ok=True)
                for i, (origin, data) in enumerate(files, 1):
                    (page_dir / f"source-{i}.md").write_text(classify(spec_dir.name, version_dir.name, origin, data), encoding="utf-8")
                (page_dir / "index.md").write_text(
                    f"---\ntitle: TS {spec_dir.name} {version_dir.name}\nsidebar_position: 1\n---\n\n"
                    + f"# TS {spec_dir.name} {version_dir.name}\n\n"
                    + "\n".join(f"- [Source {i}](./source-{i})" for i in range(1, len(files) + 1))
                    + "\n",
                    encoding="utf-8",
                )
                spec_versions.append(version_dir.name)
            if spec_versions:
                spec_dir_out = OUTPUT / spec_dir.name
                spec_dir_out.mkdir(parents=True, exist_ok=True)
                (spec_dir_out / "index.md").write_text(
                    f"---\ntitle: TS {spec_dir.name}\nsidebar_position: {len(specs) + 1}\n---\n\n"
                    + f"# TS {spec_dir.name}\n\n"
                    + "\n".join(f"- [{v}](./{v}/)" for v in spec_versions)
                    + "\n",
                    encoding="utf-8",
                )
                specs.append(spec_dir.name)
    links = "\n".join(f"- [TS {spec}](./{spec}/)" for spec in specs) or "No supported specification DOCX files found."
    (OUTPUT / "index.md").write_text(f"---\ntitle: 3GPP Specifications\nsidebar_position: 1\n---\n\n# 3GPP Specifications\n\n{links}\n", encoding="utf-8")
    if specs:
        print(f"Generated Docusaurus pages for specifications: {', '.join(specs)}")
    else:
        print(f"No supported DOCX sources found under {SOURCE_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
