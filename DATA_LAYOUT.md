# Visual inspection data layout

Git contains the application, documentation, generic profile manifests, and validation
code. Approved private files live in SharePoint and are never committed.

## Private source workspace

An owner organizes customer deliveries locally before creating bundles:

```text
private-data/
├── raw/
│   └── core/                         Extracted evaluation corpus
├── derived/
│   ├── round1/                       Curated first examples
│   └── workshop-evaluation/          Labeled workshop subset
├── received/
│   └── originals/                    Exact files as received, unchanged
└── manifests/
    └── received-files.json           Size, SHA-256, integrity, and notes
```

The full profile preserves invalid or incomplete received files unchanged and marks
their integrity in the manifest. It never presents an invalid archive as usable data.

## SharePoint layout

```text
Physical AI Visual Inspection/
├── workshop/
│   └── 2026.08.15/
│       ├── visual-inspection-workshop-2026.08.15.tar
│       └── visual-inspection-workshop-2026.08.15.tar.json
├── full/
│   └── 2026.08.15/
│       ├── visual-inspection-full-2026.08.15.tar
│       └── visual-inspection-full-2026.08.15.tar.json
└── received/
    └── originals/                    Individually browsable original deliveries
```

The workshop bundle contains only curated and approved evaluation pairs. The restricted
full bundle additionally contains the extracted corpus and every preserved original
delivery. Keeping originals separately browsable in SharePoint makes it possible to
retrieve one source file without downloading the full bundle.

## Brev cache

```text
$HOME/workspace/visual-inspection-data/
├── versions/
│   ├── workshop/2026.08.15/
│   └── full/2026.08.15/
└── current -> versions/<profile>/<version>
```

On first launch, `scripts/fetch-data.py` downloads the selected bundle through an
approved SharePoint link, verifies the bundle SHA-256, rejects unsafe archive entries,
verifies every internal file, and atomically switches `current`. Later starts of the
same instance reuse the verified cache. A new instance needs a valid link again.

## Rules

- Keep exact received files immutable under `received/originals`.
- Keep extracted or generated files under `raw` and `derived`.
- Never put private data, SharePoint links, credentials, or inference evidence in Git.
- Use read-only SharePoint links with explicit recipients when headless download is
  supported, or an approved expiring download link for automated Brev startup.
- Do not enable **Block download** on a link used by the setup script.
- Treat the SharePoint URL as a secret; do not print, persist, or add it as a reusable
  Launchable default.
- Use `workshop` for attendees and `full` only for restricted evaluation instances.

## Prepare a bundle

```bash
python3 scripts/prepare-data-bundle.py \
  workshop /path/to/private-data \
  /path/to/visual-inspection-workshop-2026.08.15.tar
```

The adjacent `.tar.json` file records the outer bundle checksum and byte counts. Upload
both files to SharePoint. Configure `VISUAL_INSPECTION_DATA_SHA256` from that metadata,
not from an unverified copy.
