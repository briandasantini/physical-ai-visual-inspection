# Data and Privacy

The public repository and private workshop data are intentionally separate.

## Public GitHub repository

Contains:

- application and deployment code;
- documentation;
- dataset profile manifests;
- tests and agent instructions.

Does not contain:

- private images or videos;
- transfer archives;
- inference evidence;
- SharePoint links, NGC keys, or agent credentials.

## Private SharePoint data

The attendee-facing `workshop` bundle contains only the approved curated pairs and
larger evaluation subset. A separate restricted `full` bundle contains the extracted
evaluation corpus and every preserved original delivery. Original files are also kept
individually browsable in a restricted SharePoint folder.

Each bundle includes an inventory of file paths, byte sizes, and SHA-256 checksums. Brev
also verifies an outer bundle checksum before extraction. First launch downloads to
persistent storage and activates the dataset only after validation succeeds.

The extended source archive is preserved unchanged even though its received copy has
invalid header data. It is marked unusable until a replacement is received.

## Runtime handling

- Example data is mounted read-only.
- Browser uploads are processed in memory.
- The website does not persist uploads or inference outputs.
- CLI evidence is written only when the participant supplies an output path.
- Private data must never be committed to Git.
- SharePoint links must never be committed, logged, or stored as reusable defaults.
