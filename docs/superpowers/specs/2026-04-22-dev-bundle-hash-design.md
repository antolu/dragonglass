# Dev bundle hash friction — design

## Problem

`compute_deps_hash.py` includes `git describe --tags --always --dirty` in the Python bundle hash. In development, any uncommitted file marks the tree dirty, changing the hash on every edit. `BackendManager` compares the hash baked into the `.app` bundle against the installed hash — a mismatch triggers the setup window and forces a full bundle reinstall before the backend can start.

This means every Xcode Debug build after a file edit prompts for a bundle reinstall, even when no deps changed.

## Root cause

`--dirty` was added to invalidate the dev bundle when a new dragonglass wheel is built into it. In practice:
- CI/Release builds always have a clean tree, so `--dirty` is a no-op there.
- Actual dep changes (uv.lock, package.json) are already captured by hashing those files directly — the git version is redundant for that.
- The only thing `--dirty` accomplishes in practice is breaking the dev workflow.

## Solution

Two changes:

### 1. Remove `--dirty` from `compute_deps_hash.py`

`scripts/compute_deps_hash.py:25` — change:
```
["git", "describe", "--tags", "--always", "--dirty"]
```
to:
```
["git", "describe", "--tags", "--always"]
```

This still invalidates bundles on new commits (new wheel), but dirty state no longer affects the hash.

### 2. Debug builds write `dev` as the bundle hash

The Xcode build phase that produces `python_bundle_hash.txt` branches on `$CONFIGURATION`:

- **Release**: runs `scripts/compute_deps_hash.py --type python`, writes the real 12-char hash (unchanged)
- **Debug**: writes the literal string `dev`

### 3. `BackendManager` skips the hash check for `dev`, with env-var override

In `startBackend()` (`BackendManager.swift`), replace the current `depsHashChanged` logic with:

```swift
let isDevHash = bundledDepsHash == "dev"
let forceInstall = ProcessInfo.processInfo.environment["DRAGONGLASS_FORCE_BUNDLE_INSTALL"] == "1"
let depsHashChanged = !isDevHash && bundledDepsHash != nil && bundledDepsHash != installedDepsHash
let needsBundle = forceInstall || pythonChanged || !dragonglassExists || depsHashChanged
```

When `bundledDepsHash == "dev"`, `depsHashChanged` is always false — the app skips straight to startup as long as the venv exists.

To test bundle installs in a Debug build, set `DRAGONGLASS_FORCE_BUNDLE_INSTALL=1` in the Xcode scheme's environment variables. This forces `needsBundle = true` regardless of hash state.

## What doesn't change

- Release builds: identical behaviour to today
- `isDevVersion` logic and the offline install path: unchanged
- Bundle hash verification during extraction: unchanged
- CI bundle build scripts: unchanged

## Files to touch

| File | Change |
|------|--------|
| `scripts/compute_deps_hash.py` | Remove `--dirty` flag |
| Xcode build phase (python_bundle_hash.txt) | Branch on `$CONFIGURATION` |
| `DragonglassApp/Dragonglass/BackendManager.swift` | Update `needsBundle` logic |
