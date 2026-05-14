# VelaFlow V7.8 Stable Candidate Freeze

V7.8 creates a rollback point before V8 or packaging work.

## Freeze Target

```text
VelaFlow V7.7 Stable Candidate 1
```

## Policy

After creating a stable candidate snapshot, the core pipeline should not be
changed except for bug fixes. New V8 work should be developed with this
snapshot available as release evidence and rollback context.

## Snapshot Evidence

The **Create Stable Candidate Snapshot** button exports:

- `STABLE_BUILD.md`
- `stable_manifest.json`
- `project_snapshot.json`
- production audit JSON/Markdown
- diagnostic ZIP
- beta report JSON/Markdown when a beta session is selected
- optional smoke test JSON result
- ZIP archive of the snapshot folder

Output path:

```text
outputs/stable_candidates/<project_name>/stable_candidate_<timestamp>/
```

## UI

Stable Candidate Freeze is available from:

- Project Dashboard > Stable Candidate Freeze
- Beta Test Mode > Stable Freeze

## Not Included

V7.8 does not add online licensing, payment, cloud sync, full video AI, auto
upload, or installer packaging.
