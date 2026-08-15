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
- NGC or agent credentials.

## Private NGC resources

The attendee-facing `workshop` resource contains only the approved curated pairs and
larger evaluation subset. A separate restricted `full` resource can hold validated raw
and derived data without granting workshop attendees access to the entire corpus.

Each resource version includes an inventory of file paths, byte sizes, and SHA-256
checksums. First launch downloads to persistent Brev storage and activates the dataset
only after validation succeeds.

## Runtime handling

- Example data is mounted read-only.
- Browser uploads are processed in memory.
- The website does not persist uploads or inference outputs.
- CLI evidence is written only when the participant supplies an output path.
- Private data must never be committed to Git.
