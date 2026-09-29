# N1 Portal Validator Checklist

Check changed behavior and relevant regressions. Mark only applicable items; an absent data source is not evidence of a pass and must remain explicitly unavailable.

- [ ] Sidebar keeps N1 → specification → General/Common Rules and Messages → Message → IE, plus Referenced Specifications; all extracted messages remain in source order, selecting one expands its IEs in place, and clicking it again collapses them; no Procedures menu.
- [ ] Sidebar has no TRACE/trace-change glyphs. IE support dots are small and use green Supported, red Not Supported, gray N/A.
- [ ] Version selector exists above the sidebar hierarchy; switching versions updates available content and keeps the selected page when it exists.
- [ ] Specification wording, headings, notes, tables, field/value definitions, and references remain source-faithful, including merged source-table cells. Message IE Table keeps the source columns (Information element, Presence, IEI, Length, Reference) and adds only Stack; selecting an IE name opens its corresponding detail; IE Structure keeps Octet/Bit/Field/Value/Reference where present.
- [ ] IE detail retains Specification, Version, Stack Support, specification content, Message IE Table, IE structure, field descriptions, referenced specification, Version History, Trace, and Diff where the inputs exist.
- [ ] Version History has All Versions and Changes Only views and marks Stack/specification changes only from actual version data.
- [ ] Referenced clauses (including TS 24.008) link from actual citations or explicit mappings, show source content and an Open full clause link when present, and say “Reference source not available” when absent.
- [ ] Trace is available as a detail view with actual Raw and Decoded data when mapped; no sample is presented as real evidence.
- [ ] Trace and Diff are separate detail tabs. Raw Trace reflects actual stack output; Decoded Trace shows actual Message/IE/Field/Value data.
- [ ] Diff compares actual specification text, tables, IE structure, fields, values, and available Raw/Decoded Trace data across two versions. Removed values are red; added values are green. If actual comparison is unavailable, controls are disabled and any retained UI example is labeled Sample.
- [ ] Show Diff does not resize the IE Structure table, Diff table, columns, or side-by-side panels; long values wrap without breaking layout.
- [ ] TS 24.008 references resolve only from explicit source/mapping data; missing source says “Reference source not available”.
- [ ] Upload path is `spec-source/<spec>/<version>/`; processing handles 3GPP ZIP and DOC/DOCX content, extracts headings/clauses/paragraphs/tables/messages/IEs/structure/fields/notes/references, and does not make PDF OCR the default.
- [ ] Push pipeline runs extraction, reference resolution, version Diff generation, Stack mapping, Trace mapping, Docusaurus build, then static GitHub Pages deployment. No persistent server is introduced.
- [ ] Stack mapping reports status only from available evidence; no Code/Encode/Decode/Test/Trace sub-statuses are shown in the final UI.
- [ ] For requested C++ Stack implementation, Gap Analysis precedes coding; check the exact spec/reference, analogous IE, project conventions, class/message integration, Encode/Decode, unit tests, build, and Trace against evidence. Never infer fields or values from missing specification text.
- [ ] Existing behavior outside the requested change remains intact; no unrelated UI/menu removal, generated content deletion, deployment, or push occurred.
