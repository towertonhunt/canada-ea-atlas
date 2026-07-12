# Working locally (macOS / Mac mini)

Everything in this project lives in git, so "migrating to local" = cloning
the repo. The map, search, and project pages are static files; the build
and analysis scripts are near-pure Python stdlib. No database server, no
Node build step.

## 1. Prerequisites (one time)

macOS ships with git and Python 3, but the Command Line Tools give you
current versions:

```sh
xcode-select --install          # git + toolchain (skip if already installed)
python3 --version               # need 3.10+ ; macOS has it, or: brew install python
```

That's the whole toolchain for local development. The two extra libraries
the project uses — `openpyxl` and `pypdf` — are only needed by the
GitHub Actions harvest lanes, which run in the cloud, not on your Mac. If
you ever want to run a lane's Python locally:

```sh
python3 -m pip install --user openpyxl pypdf
```

## 2. Clone the repo + check out the working branch

```sh
cd ~/Projects                                   # wherever you keep code
git clone https://github.com/towertonhunt/ontario-rea-map.git
cd ontario-rea-map
git checkout claude/mac-mini-connection-ceehl5  # the active work branch
```

First clone pulls ~320 MB (data + git history). HTTPS will prompt for your
GitHub login; if you use 2FA, create a Personal Access Token (GitHub →
Settings → Developer settings → Tokens) and use it as the password, or set
up SSH and clone `git@github.com:towertonhunt/ontario-rea-map.git`.

## 3. Verify the clone

```sh
python3 scripts/validate_data.py       # should end with "All checks passed."
```

## 4. View the site locally

The site is static — serve the folder and open it:

```sh
python3 -m http.server 8000            # then visit http://localhost:8000
```

- Map: <http://localhost:8000/index.html>
- Search: <http://localhost:8000/search.html>
- A project page: `http://localhost:8000/project.html?id=<id>` (ids live in
  `data/api/projects.json`)

(Open with a server, not a `file://` path — the pages fetch JSON, which
browsers block over `file://`.)

## 5. Rebuild data after edits

```sh
python3 scripts/build_national_geojson.py   # 1. rebuild the map
python3 scripts/gap_reconcile.py            # 2. refresh the gap report/overlay
python3 scripts/build_api.py                # 3. rebuild the app API (must run after 1)
python3 scripts/validate_data.py            # 4. integrity check
```

Rebuild order matters: `build_api` reads the geojson, so run it after
`build_national_geojson`. `validate_data` will FAIL if the api row count
and geojson feature count disagree — that's the guard that they're in sync.

## 6. How local and the cloud stay in sync

- **Scheduled Actions lanes keep running on GitHub** regardless of your
  local clone — they harvest registries and commit `[skip ci]` data to
  this branch. Your local copy drifts behind as they run.
- Pull their work before starting a local session:
  ```sh
  git pull --rebase origin claude/mac-mini-connection-ceehl5
  ```
- Push your local changes back to the same branch:
  ```sh
  git push origin claude/mac-mini-connection-ceehl5
  ```
  If a lane pushed while you worked, the push is rejected; resolve with
  `git pull --rebase` then push again.
- **The dev sandbox has no general internet — all fetching must run on
  Actions.** Locally you can do everything *except* the harvest lanes:
  build, reconcile, validate, view, edit. To fetch new data, trigger the
  workflow on GitHub (Actions tab → the lane → "Run workflow"), then pull.

## 7. Keep working with Claude on the Mac mini (optional)

Install the Claude Code CLI and run it inside the clone to keep the same
assistant workflow locally:

```sh
npm install -g @anthropic-ai/claude-code   # or see claude.ai/code for installers
cd ~/Projects/ontario-rea-map
claude
```

It reads `CLAUDE.md` on start, so it picks up full project context. Note
a local Claude session *can* reach the internet for fetches (unlike the
cloud sandbox), but the durable automation should stay in the Actions
lanes so it runs unattended.

## What deploys the public site

`rea.towerton.ca` is GitHub Pages served from `main`. Work happens on
`claude/mac-mini-connection-ceehl5`; publishing = merging the branch to
`main`. Local edits are not public until merged.
