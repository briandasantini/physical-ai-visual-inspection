# Visual inspection data layout

The Launchable keeps application code and customer data separate. Git contains the
application and data profile manifests. Versioned private NGC resources contain the
actual customer files.

```text
/home/nvidia/visual-inspection/
├── app/
│   └── launchable/                 Clean application and deployment files
├── data/
│   ├── raw/
│   │   ├── core/                   Canonical private image dataset
│   │   ├── extended/               Reserved for validated extended dataset
│   │   └── source-videos/          Original source videos
│   ├── derived/
│   │   ├── round1/                 Curated first examples
│   │   ├── workshop-evaluation/   Labeled larger-set workshop subset
│   │   ├── workshop-pairs/         Curated reference/live pairs
│   │   ├── demo-frames/            Frames generated for prototype testing
│   │   └── slide-assets/           Images extracted for workshop slides
│   ├── archives/                   Original transfer archives
│   └── manifests/
│       └── catalog.json            File counts, bytes, and extensions
└── logs/                           Setup and rehearsal logs
```

For new Launchable instances, the persistent cache is stored under:

```text
$HOME/workspace/visual-inspection-data/
├── versions/
│   ├── workshop/2026.08.13/        Curated workshop resource
│   └── full/2026.08.13/            Full private corpus resource
└── current -> versions/<profile>/<version>
```

## Rules

- Keep original images immutable under `data/raw`.
- Put generated, paired, resized, or annotated images under `data/derived`.
- Keep transfer archives until extracted contents pass count and size checks.
- Do not include customer data in the public Launchable repository or container image.
- Use the `workshop` profile for attendee-facing instances.
- Use the `full` profile only for private evaluation instances.
- Treat uploads and model outputs as ephemeral unless an explicit experiment export is requested.

## Lifecycle

1. An owner organizes approved files once under the layout above.
2. Owners prepare attendee-facing, manifest-indexed curated and evaluation collections.
3. `prepare-data-resource.py` stages only the paths listed in `data/profiles.json`.
4. `publish-data-resource.sh` publishes an immutable version to NGC Private Registry.
5. `setup.sh` downloads and validates every file path, size, and SHA-256 on the first launch.
6. Later container restarts and Brev stop/start cycles reuse the local `current` cache.
7. A newly created or deleted-and-recreated instance downloads the pinned version again.

The full corpus never belongs in Git. Git is for reproducible code and manifests;
NGC Private Registry is the private system of record for the dataset artifacts.

## Publish a version

Create the private NGC resource once, then publish a profile version:

```bash
export NGC_API_KEY=<scoped-key>
export VISUAL_INSPECTION_DATA_RESOURCE=<org>/<team>/visual-inspection-workshop-data
export VISUAL_INSPECTION_DATA_VERSION=2026.08.13

./scripts/publish-data-resource.sh \
  workshop /home/nvidia/visual-inspection/data \
  /home/nvidia/visual-inspection/resource-staging/workshop-2026.08.13
```

Use a separate private resource name for the `full` profile so workshop access never
implicitly grants access to the full corpus.

## Refresh the manifest

```bash
python3 /home/nvidia/visual-inspection/app/scripts/catalog-data.py \
  /home/nvidia/visual-inspection/data \
  --output /home/nvidia/visual-inspection/data/manifests/catalog.json
```
