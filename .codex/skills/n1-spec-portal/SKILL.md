---
name: n1-spec-portal
description: >-
  Develop, repair, or review the Docusaurus 3GPP N1 Specification Portal in /data/website.
  Use for changes to TS 24.501/24.008 extraction, versions, navigation, Message/IE views,
  references, Stack mapping, Trace, Diff, GitHub Actions, or Pages. Coordinates only the
  Developer and Validator roles; use again for follow-up fixes or revalidation.
---

# N1 Specification Portal Harness

Use the two persistent roles in `.codex/agents/`: `n1-portal-developer` and `n1-portal-validator`. The parent session coordinates the handoff. Do not add standing roles or split work into more agents.

## Workflow

1. Identify the requested behavior and applicable requirements. Inspect the affected flow and files before editing. Read the relevant section of `rules/validator-checklist.md`; read the whole checklist when changing shared UI, navigation, version data, generated content, or pipeline behavior.
2. Have Developer implement the narrowest complete change. Preserve existing behavior and any pre-existing user modifications. Do not deploy or push unless requested.
3. Developer runs the smallest relevant check and a production build for site-affecting changes, then reports files and results.
4. Have Validator independently inspect the changed files and applicable checklist items, plus only the related existing features.
5. On FAIL, send only actionable findings to Developer. Developer fixes only those findings and Validator rechecks. Repeat until PASS; otherwise leave the task explicitly incomplete.

Do not claim a capability works from a mockup. Specification text and tables must come from source documents. Unknown references, Stack support, Trace, and version changes stay unavailable or explicitly unconfigured until evidence is present. Current known state: V19.0.0 source ZIPs are present; Stack and Trace are not connected; with one uploaded version per specification, cross-version Diff/history is not yet evidence-backed.

## Scope invariants

- N1 is the initial scope: TS 24.501 and only the TS 24.008 clauses actually referenced. Keep navigation organized as specification → clause/message → IE, plus referenced specifications. Do not create a Procedures menu.
- Keep the version selector above the specification navigation and preserve the selected page when changing versions where data exists.
- Sidebar support dots mean Supported, Not Supported, or N/A. Derive one status from the Stack Support Evidence Set (Code, Encode, Decode, Test, Trace); show Trace details only in detail views.
- Preserve source wording and table columns, including Message IE and IE structure fields. Never synthesize missing specification content.
- Keep specification, Trace, and Diff views distinct. Diff must compare actual version content and use red for removed and green for added content; unavailable inputs must be reported as unavailable.
- Upload changes flow through extraction, reference resolution, diff/mapping generation, Docusaurus build, and GitHub Pages workflow. Retain static hosting without a server.
- Existing functionality takes precedence over convenience refactors. Keep the fixed regression checklist current when requirements change.
