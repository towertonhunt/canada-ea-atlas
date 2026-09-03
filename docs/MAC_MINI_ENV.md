# Mac mini Environment Probe

Read-only environment probe of Kyle's M4 Mac mini, run via the Claude Code bridge.

**Probe date:** 2026-09-02

## System

| Item | Value |
| --- | --- |
| Hostname | `Kyles-Mac-mini.local` |
| Kernel | `Darwin 25.5.0` (xnu-12377.121.6~2, `arm64`, T8132 / Apple M4) |
| macOS | 26.5.1 (build 25F80) |
| User | `aiassistant` |
| Home / cwd | `/Users/aiassistant` |

## Tooling

| Tool | Path | Version |
| --- | --- | --- |
| `brew` | `/opt/homebrew/bin/brew` | — |
| `psql` | `/opt/homebrew/opt/postgresql@17/bin/psql` | 17.7 (Homebrew) |
| `python3` | `/usr/bin/python3` (system) | 3.9.6 |
| `node` | `/opt/homebrew/bin/node` | v25.5.0 |
| `qgis` | not on `PATH` | GUI apps present: `/Applications/QGIS.app`, `/Applications/QGIS-final-4_0_0.app` |
| `rclone` | `/opt/homebrew/bin/rclone` | v1.75.0 |
| `tailscale` | not found | no `/Applications/Tailscale.app` |

Note: Homebrew also ships `python3.14` at `/opt/homebrew/bin/python3.14`; bare `python3`
resolves to the macOS system Python 3.9.6.

## PostgreSQL

- `pg_isready`: `/tmp:5432 - accepting connections`
- `brew services`: `postgresql@17  started  aiassistant  ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist`
- Server version: 17.7 (Homebrew)

### Databases

- `enviro_permits`
- `postgres`
- `template0`
- `template1`

### PostGIS (`enviro_permits`)

`SELECT postgis_version()` → `3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1`

Installed extensions:

| Extension | Version |
| --- | --- |
| `postgis` | 3.6.1 |
| `pg_trgm` | 1.6 |
| `plpgsql` | 1.0 |

The `public` schema contains 35 tables.

## Repository clone

`mdfind -name canada-ea-atlas` returned nothing (the local directory is not named after the
repo), but the clone exists at:

**`~/Projects/ea-atlas/map`**

- Remote `origin`: `https://github.com/towertonhunt/canada-ea-atlas.git` (fetch and push)
- Branch at probe time: `main`, working tree clean (`git status --porcelain` → 0 entries)
- Local branches before this probe: `main` only

Sibling directories under `~/Projects/ea-atlas/`: `archive`, `enviro-permits`, `federal-ea`,
`map`, `ontario-classea`, `pipeline`, plus `PROJECT.md`, `ECONOMIC_BASELINES.md`,
`MOVE_MANIFEST.md`.

Other `~/Projects` entries: `ccfn-disturbance` (git, no remote), `gdrive-proton-migration`,
`unceded-futures`.

`~/code` exists but is empty.

## Disk

| Filesystem | Size | Used | Avail | Capacity | Mounted on |
| --- | --- | --- | --- | --- | --- |
| `/dev/disk3s1s1` | 228Gi | 16Gi | 47Gi | 26% | `/` |

## Rod Northey EA-book digitization

`mdfind "Northey"` returned no results (Spotlight indexing appears not to cover these paths),
but a filename search found material under `~/Projects/ea-atlas/federal-ea/`:

- `Northey 2023/` (directory)
- `northey_2023_part1_complete.md`
- `Northey_IAA_2023_working_draft.pdf`

A prior Claude Code session directory also exists for `~/Documents/Northey 2023`.
