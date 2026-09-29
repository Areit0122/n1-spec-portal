#!/usr/bin/env python3
"""Extract clause headings and message IE tables from 3GPP DOCX sources."""

from __future__ import annotations

import re
import shutil
import sys
import json
import unicodedata
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


def anchor(number: str, title: str) -> str:
    text = f"{number.replace('.', '').lower()}-{title.lower()}"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9_-]+", "-", text).strip("-")


def message_catalog(spec: str, version: str, markdown: str, origin: str) -> dict:
    message_pattern = r"8\.[23]\.\d+[AB]?" if spec == "24.501" else r"9\.\d+\.\d+[AB]?"
    heading = re.compile(r"^#{2,6}\s+(\d+(?:\.\d+)*[AB]?)\s+(.+)$")
    messages = []
    clauses = []
    references = []
    current = None
    current_clause = None
    table = False
    headers = []
    lines = markdown.splitlines()
    for line_index, line in enumerate(lines):
        match = heading.match(line)
        if match:
            number, title = match.groups()
            entry = {"number": number, "title": title, "anchor": anchor(number, title), "level": len(line) - len(line.lstrip("#")), "line": line_index}
            clauses.append(entry)
            current_clause = entry
            if line.startswith("####") and re.fullmatch(message_pattern, number) and MESSAGE.search(title):
                current = {key: value for key, value in entry.items() if key not in ("line", "level")}
                current["ies"] = []
                messages.append(current)
            elif not number.startswith(("8.2.", "8.3.") if spec == "24.501" else ("9.",)):
                current = None
            table = False
            continue
        for ref in re.finditer(r"\b(?:3GPP\s+)?TS\s+(\d{2}\.\d{3})\b([^\n]{0,100})", line, re.I):
            target_spec = ref.group(1)
            if target_spec == spec:
                continue
            clause_match = re.search(r"\b(?:sub)?clause\s+(\d+(?:\.\d+)+(?:[A-Z])?)", ref.group(2), re.I)
            references.append({
                "fromClause": current_clause["number"] if current_clause else None,
                "fromAnchor": current_clause["anchor"] if current_clause else None,
                "spec": target_spec,
                "clause": clause_match.group(1) if clause_match else None,
            })
        if line.startswith("#### Message IE table — "):
            table = current is not None
            headers = []
            continue
        if not table:
            continue
        if not line.strip():
            continue
        if not line.startswith("|"):
            table = False
            continue
        cells = [cell.strip().replace("\\|", "|") for cell in line.strip("|").split("|")]
        if not headers:
            headers = cells
        elif all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        elif len(cells) == len(headers):
            row = dict(zip(headers, cells))
            reference = re.search(r"(?<![\d.])\d+(?:\.\d+)+[A-Z]?(?![\d.])", row.get("Type/Reference", ""))
            current["ies"].append({
                "name": row.get("Information Element", ""),
                "presence": row.get("Presence", ""),
                "iei": row.get("IEI", ""),
                "format": row.get("Format", ""),
                "length": row.get("Length", ""),
                "reference": reference.group(0) if reference else "",
                "rawReference": row.get("Type/Reference", ""),
            })
    needed = {ie["reference"] for message in messages for ie in message["ies"] if ie["reference"]}
    for clause in clauses:
        if clause["number"] not in needed:
            continue
        end = next((item["line"] for item in clauses if item["line"] > clause["line"] and item["level"] <= clause["level"]), len(lines))
        clause["content"] = "\n".join(lines[clause["line"] + 1:end]).strip()[:12000]
    for clause in clauses:
        clause.pop("line", None)
        clause.pop("level", None)
    references = list({(r["fromClause"], r["spec"], r["clause"]): r for r in references}.values())
    archive = re.match(r"(\d{5}-[a-z]\d{2}\.zip):", origin, re.I)
    source_url = f"https://www.3gpp.org/ftp/Specs/archive/24_series/{spec}/{archive.group(1)}" if archive else None
    return {"spec": spec, "version": version, "sourceUrl": source_url, "messages": messages, "clauses": clauses, "references": references}


def self_test() -> None:
    fixture = """#### 8.2.1 Authentication request

#### Message IE table — 8.2.1 Authentication request

| IEI | Information Element | Type/Reference | Presence | Format | Length |
| --- | --- | --- | --- | --- | --- |
| — | ngKSI | NAS key set identifier9.11.3.32 | M | V | 1/2 |

### 4 General
As specified in 3GPP TS 24.008 [1], subclause 10.5.1.
"""
    result = message_catalog("24.501", "19.0.0", fixture, "24501-j00.zip:24501-j00.docx")
    assert result["sourceUrl"] == "https://www.3gpp.org/ftp/Specs/archive/24_series/24.501/24501-j00.zip"
    assert result["messages"][0]["ies"][0]["reference"] == "9.11.3.32"
    assert result["messages"][0]["ies"][0]["presence"] == "M"
    assert result["references"][0]["clause"] == "10.5.1"


def main() -> int:
    specs = []
    catalog = []
    version_map_path = ROOT / "mapping" / "references.json"
    version_map = json.loads(version_map_path.read_text(encoding="utf-8")) if version_map_path.exists() else {}
    # ponytail: rebuild this generated-only subtree so removed input versions vanish on the next run.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    content_output = ROOT / "static" / "spec-content"
    if content_output.exists():
        shutil.rmtree(content_output)
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
                    markdown = classify(spec_dir.name, version_dir.name, origin, data)
                    (page_dir / f"source-{i}.md").write_text(markdown, encoding="utf-8")
                    static_page = ROOT / "static" / "spec-content" / spec_dir.name / version_dir.name
                    static_page.mkdir(parents=True, exist_ok=True)
                    (static_page / f"source-{i}.md").write_text(markdown, encoding="utf-8")
                    entry = message_catalog(spec_dir.name, version_dir.name, markdown, origin)
                    configured = version_map.get(f"{spec_dir.name}@{version_dir.name}", {})
                    for reference in entry["references"]:
                        target_version = configured.get(reference["spec"])
                        target = next((item for item in catalog if item["spec"] == reference["spec"] and item["version"] == target_version), None)
                        target_clause = next((clause for clause in target["clauses"] if clause["number"] == reference["clause"]), None) if target and reference["clause"] else None
                        reference["targetVersion"] = target_version
                        reference["status"] = "resolved" if target_clause else "unresolved" if not target_version else "missing_source" if not target else "missing_clause"
                        reference["targetAnchor"] = target_clause["anchor"] if target_clause else None
                    catalog.append(entry)
                (page_dir / "index.md").write_text(
                    f"---\ntitle: TS {spec_dir.name} V{version_dir.name}\nsidebar_position: 1\n---\n\n"
                    + f"# TS {spec_dir.name} V{version_dir.name}\n\n"
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
    (ROOT / "static" / "spec-catalog.json").write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    if specs:
        print(f"Generated Docusaurus pages for specifications: {', '.join(specs)}")
    else:
        print(f"No supported DOCX sources found under {SOURCE_ROOT}")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
        print("classifier self-test passed")
        raise SystemExit(0)
    raise SystemExit(main())
