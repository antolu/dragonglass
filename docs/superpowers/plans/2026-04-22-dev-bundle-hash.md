# Dev Bundle Hash Friction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate spurious bundle reinstall prompts during Xcode Debug builds by writing `dev` as the bundle hash in Debug configuration and skipping the hash staleness check in `BackendManager`.

**Architecture:** Three targeted changes — remove `--dirty` from the hash script, branch the Xcode build phase on `$CONFIGURATION`, and update the `needsBundle` logic in Swift to skip the check when `bundledDepsHash == "dev"` (with a `DRAGONGLASS_FORCE_BUNDLE_INSTALL` env-var escape hatch).

**Tech Stack:** Python 3.11+, bash, Swift/SwiftUI, Xcode build phases, pytest

---

## File map

| File | Change |
|------|--------|
| `scripts/compute_deps_hash.py` | Remove `--dirty` flag from `git describe` call |
| `tests/test_compute_deps_hash.py` | Fix `test_python_hash_matches_manual_sha256` to include all hash inputs |
| `DragonglassApp/scripts/bundle_resources.sh` | Branch on `$CONFIGURATION` to write `dev` in Debug |
| `DragonglassApp/Dragonglass/BackendManager.swift` | Update `needsBundle` logic — skip check for `dev` hash, add force-install env var |

---

### Task 1: Remove `--dirty` from `compute_deps_hash.py`

**Files:**
- Modify: `scripts/compute_deps_hash.py:25`

- [ ] **Step 1: Edit `compute_deps_hash.py`**

In `scripts/compute_deps_hash.py`, change line 25 from:
```python
            ["git", "describe", "--tags", "--always", "--dirty"],
```
to:
```python
            ["git", "describe", "--tags", "--always"],
```

The full `compute_hash` function should now look like:
```python
def compute_hash(type_: str, root: pathlib.Path) -> str:
    h = hashlib.sha256()
    if type_ == "python":
        h.update((root / "uv.lock").read_bytes())
        h.update((root / "DragonglassApp/opencode/package.json").read_bytes())
        try:
            import subprocess  # noqa: PLC0415

            version = subprocess.check_output(
                ["git", "describe", "--tags", "--always"],
                cwd=root,
                stderr=subprocess.DEVNULL,
            ).strip()
            h.update(version)
        except Exception:
            pass
    elif type_ == "opencode":
        h.update((root / "DragonglassApp/opencode/package.json").read_bytes())
    else:
        raise ValueError(f"unknown type: {type_!r}")
    return h.hexdigest()[:12]
```

- [ ] **Step 2: Fix `test_python_hash_matches_manual_sha256`**

The existing test at `tests/test_compute_deps_hash.py:36-45` manually computes the hash using only `uv.lock`, but the real hash includes `package.json` and the git version too. The test passes today only because it happens to match — after removing `--dirty` the git-version component changes, but more importantly the test is wrong. Fix it to match the real computation:

```python
def test_python_hash_matches_manual_sha256() -> None:
    import subprocess
    h = hashlib.sha256()
    h.update(pathlib.Path("uv.lock").read_bytes())
    h.update(pathlib.Path("DragonglassApp/opencode/package.json").read_bytes())
    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"],
            stderr=subprocess.DEVNULL,
        ).strip()
        h.update(version)
    except Exception:
        pass
    expected = h.hexdigest()[:12]
    result = subprocess.run(
        [sys.executable, "scripts/compute_deps_hash.py", "--type", "python"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == expected
```

- [ ] **Step 3: Run the hash tests**

```bash
pytest tests/test_compute_deps_hash.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 4: Run pre-commit**

```bash
pre-commit run --all-files
```

Expected: all hooks pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/compute_deps_hash.py tests/test_compute_deps_hash.py
git commit -m "fix(bundle): remove --dirty from deps hash git describe"
```

---

### Task 2: Debug builds write `dev` as bundle hash

**Files:**
- Modify: `DragonglassApp/scripts/bundle_resources.sh:97-98`

- [ ] **Step 1: Branch on `$CONFIGURATION` in `bundle_resources.sh`**

Replace lines 97-98 in `DragonglassApp/scripts/bundle_resources.sh`:
```bash
# Compute Python deps hash and write resource file
PY_HASH="$("$_PY" "$SRCROOT/../scripts/compute_deps_hash.py" --type python --root-dir "$SRCROOT/..")"
printf "%s\n" "$PY_HASH" > "$RESOURCES_DIR/python_bundle_hash.txt"
```

with:
```bash
# Compute Python deps hash and write resource file
# Debug builds use a sentinel so the app skips the hash staleness check.
if [ "${CONFIGURATION}" = "Debug" ]; then
  PY_HASH="dev"
else
  PY_HASH="$("$_PY" "$SRCROOT/../scripts/compute_deps_hash.py" --type python --root-dir "$SRCROOT/..")"
fi
printf "%s\n" "$PY_HASH" > "$RESOURCES_DIR/python_bundle_hash.txt"
```

Note: the rest of the script uses `$PY_HASH` for bundle building and stale-cache cleanup. When `PY_HASH=dev`, the bundle build loop will attempt to build bundles under `build/bundles/dev/` — that's harmless for Debug (it just won't find anything meaningful), but to avoid wasted build time in Debug you can guard the bundle-building section too. Add an early-exit after writing the hash file:

```bash
printf "%s\n" "$PY_HASH" > "$RESOURCES_DIR/python_bundle_hash.txt"

# In Debug builds, skip bundle building — the app uses an existing installed venv.
if [ "${CONFIGURATION}" = "Debug" ]; then
  echo "Debug build: skipping bundle build (hash=dev)"
  exit 0
fi
```

The full relevant section of `bundle_resources.sh` after the edit (lines ~96 onward):
```bash
# Compute Python deps hash and write resource file
# Debug builds use a sentinel so the app skips the hash staleness check.
if [ "${CONFIGURATION}" = "Debug" ]; then
  PY_HASH="dev"
else
  PY_HASH="$("$_PY" "$SRCROOT/../scripts/compute_deps_hash.py" --type python --root-dir "$SRCROOT/..")"
fi
printf "%s\n" "$PY_HASH" > "$RESOURCES_DIR/python_bundle_hash.txt"

# In Debug builds, skip bundle building — the app uses an existing installed venv.
if [ "${CONFIGURATION}" = "Debug" ]; then
  echo "Debug build: skipping bundle build (hash=dev)"
  exit 0
fi

# Build Python dependency bundles for all available Python versions
BUNDLE_CACHE_DIR="$SRCROOT/../build/bundle_cache"
...
```

- [ ] **Step 2: Verify the script is syntactically valid**

```bash
bash -n DragonglassApp/scripts/bundle_resources.sh
```

Expected: no output (exits 0).

- [ ] **Step 3: Commit**

```bash
git add DragonglassApp/scripts/bundle_resources.sh
git commit -m "fix(bundle): write 'dev' hash in Debug builds, skip bundle build"
```

---

### Task 3: Update `BackendManager` to skip hash check for `dev`

**Files:**
- Modify: `DragonglassApp/Dragonglass/BackendManager.swift:115-116`

- [ ] **Step 1: Replace `depsHashChanged` / `needsBundle` lines**

In `BackendManager.swift`, replace lines 115-116:
```swift
        let depsHashChanged = bundledDepsHash != nil && bundledDepsHash != installedDepsHash
        let needsBundle = pythonChanged || !dragonglassExists || depsHashChanged
```

with:
```swift
        let isDevHash = bundledDepsHash == "dev"
        let forceInstall = ProcessInfo.processInfo.environment["DRAGONGLASS_FORCE_BUNDLE_INSTALL"] == "1"
        let depsHashChanged = !isDevHash && bundledDepsHash != nil && bundledDepsHash != installedDepsHash
        let needsBundle = forceInstall || pythonChanged || !dragonglassExists || depsHashChanged
```

- [ ] **Step 2: Update the log line below to include the new variables**

Line 117 currently logs `needsBundle`, `dragonglassExists`, `pythonChanged`. Update it to also log `isDevHash` and `forceInstall` for debuggability:

```swift
        logger.info("needsBundle=\(needsBundle, privacy: .public) dragonglassExists=\(dragonglassExists, privacy: .public) pythonChanged=\(pythonChanged, privacy: .public) isDevHash=\(isDevHash, privacy: .public) forceInstall=\(forceInstall, privacy: .public)")
```

- [ ] **Step 3: Build in Xcode to verify it compiles**

Open Xcode, select the Debug scheme, press Cmd+B.

Expected: build succeeds with no errors or warnings in `BackendManager.swift`.

- [ ] **Step 4: Commit**

```bash
git add DragonglassApp/Dragonglass/BackendManager.swift
git commit -m "fix(bundle): skip hash staleness check for dev builds, add force-install env var"
```

---

## Verification

After all three tasks:

1. **Normal Debug flow** — build and run in Xcode with a dirty working tree. The app should start without opening the setup window (assuming a venv already exists from a previous install).

2. **Force-install in Debug** — in the Xcode scheme editor (`Product → Scheme → Edit Scheme → Run → Arguments → Environment Variables`), add `DRAGONGLASS_FORCE_BUNDLE_INSTALL = 1`. Build and run — the setup window should appear to install the bundle. Remove the env var after verifying.

3. **Release build unaffected** — switch scheme to Release, build. `python_bundle_hash.txt` should contain a real 12-char hex hash (verify by inspecting the app bundle: `cat path/to/Dragonglass.app/Contents/Resources/python_bundle_hash.txt`).
