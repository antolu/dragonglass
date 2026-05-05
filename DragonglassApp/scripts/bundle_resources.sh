#!/bin/bash
set -e

find_python() {
  PYPROJECT="$(dirname "$0")/../../pyproject.toml"
  MIN_MINOR="$(grep -oE 'requires-python\s*=\s*">=3\.([0-9]+)"' "$PYPROJECT" 2>/dev/null | grep -oE '[0-9]+$' || echo 11)"
  for p in "$HOME/.conda/bin/python3" "/opt/homebrew/bin/python3" "/usr/local/bin/python3" "python3"; do
    if command -v "$p" >/dev/null 2>&1; then
      if "$p" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,$MIN_MINOR) else 1)"; then
        echo "$p"
        return 0
      fi
    fi
  done
  return 1
}

find_pnpm_runner() {
  if command -v pnpm >/dev/null 2>&1; then
    echo "pnpm"
    return 0
  fi
  if command -v corepack >/dev/null 2>&1; then
    echo "corepack pnpm"
    return 0
  fi
  for path in \
    /opt/homebrew/bin/pnpm \
    /usr/local/bin/pnpm \
    "$HOME/.local/share/pnpm/pnpm" \
    "$HOME/Library/pnpm/pnpm"; do
    if [ -x "$path" ]; then
      echo "$path"
      return 0
    fi
  done
  return 1
}

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

RESOURCES_DIR="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"
mkdir -p "$RESOURCES_DIR"

_PY="$(find_python || true)"
if [ -z "$_PY" ]; then
  echo "Error: Could not find Python 3.11+" >&2
  exit 1
fi

VERSION="$(cd "$SRCROOT/.." && "$_PY" -m setuptools_scm 2>/dev/null || "$_PY" -c "import sys; sys.path.insert(0, '$SRCROOT/../'); from dragonglass._version import version; print(version)")"
printf "%s\n" "$VERSION" > "$RESOURCES_DIR/version.txt"

# Extract minimum Python version from pyproject.toml (e.g. ">=3.11" -> "3.11")
PYTHON_MIN="$("$_PY" -c "
import re, pathlib
text = pathlib.Path('$SRCROOT/../pyproject.toml').read_text()
m = re.search(r'requires-python\s*=\s*[\"\\x27]>=(\d+\.\d+)', text)
print(m.group(1) if m else '3.11')
")"
printf "%s\n" "$PYTHON_MIN" > "$RESOURCES_DIR/python_min_version.txt"

# Copy dragonglass Python source for bootstrap (needed before venv exists).
DRAGONGLASS_SRC="$SRCROOT/../dragonglass"
DRAGONGLASS_RES="$RESOURCES_DIR/dragonglass_src/dragonglass"
rm -rf "$DRAGONGLASS_RES"
cp -R "$DRAGONGLASS_SRC" "$RESOURCES_DIR/dragonglass_src/"
cp "$SRCROOT/../pyproject.toml" "$RESOURCES_DIR/dragonglass_src/"

# Write the source version so the app can detect src changes in dev/Debug builds.
printf "%s\n" "$VERSION" > "$RESOURCES_DIR/dragonglass_src_version.txt"

# Build and bundle Obsidian plugin.
PLUGIN_DIR="$SRCROOT/../obsidian-plugin"
PLUGIN_RES_DIR="$RESOURCES_DIR/ObsidianPlugin"
mkdir -p "$PLUGIN_RES_DIR"

if [ ! -d "$PLUGIN_DIR" ]; then
  echo "Error: obsidian-plugin directory not found at $PLUGIN_DIR" >&2
  exit 1
fi

PNPM_RUNNER="$(find_pnpm_runner || true)"
if [ -z "$PNPM_RUNNER" ]; then
  echo "Error: Could not find pnpm/corepack." >&2
  exit 1
fi

(
  cd "$PLUGIN_DIR"
  # shellcheck disable=SC2086
  $PNPM_RUNNER install --frozen-lockfile
  # shellcheck disable=SC2086
  $PNPM_RUNNER build
)

cp "$PLUGIN_DIR/dist/main.js" "$PLUGIN_RES_DIR/main.js"
cp "$PLUGIN_DIR/dist/manifest.json" "$PLUGIN_RES_DIR/manifest.json"

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
BUNDLE_OUTPUT_BASE="$SRCROOT/../build/bundles/$PY_HASH"
BUNDLE_RESOURCES_DIR="$RESOURCES_DIR/bundles"
mkdir -p "$BUNDLE_RESOURCES_DIR"

discover_pythons() {
  local min_minor="$1"
  local seen=""
  for dir in /opt/homebrew/bin /usr/local/bin "$HOME/.pyenv/shims" "$HOME/.pyenv/bin" "$HOME/.conda/bin"; do
    [ -d "$dir" ] || continue
    for exe in "$dir"/python3 "$dir"/python3.[0-9] "$dir"/python3.[0-9][0-9]; do
      [ -x "$exe" ] || continue
      version="$("$exe" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)" || continue
      minor="$(echo "$version" | cut -d. -f2)"
      [ "$minor" -ge "$min_minor" ] 2>/dev/null || continue
      # deduplicate by version
      case "$seen" in
        *"|$version|"*) continue ;;
      esac
      seen="$seen|$version|"
      echo "$exe $version"
    done
  done
}

MIN_MINOR="$(echo "$PYTHON_MIN" | cut -d. -f2)"

BUNDLES_ROOT="$SRCROOT/../build/bundles"
if [ -d "$BUNDLES_ROOT" ]; then
  for d in "$BUNDLES_ROOT"/*/; do
    [ -d "$d" ] || continue
    hash="$(basename "$d")"
    if [ "$hash" != "$PY_HASH" ]; then
      echo "Removing stale bundle cache: $hash"
      rm -rf "$d"
    fi
  done
fi

while IFS=" " read -r py_exe py_version; do
  [ -n "$py_exe" ] || continue
  BUNDLE_OUTPUT_DIR="$BUNDLE_OUTPUT_BASE/py$py_version"
  mkdir -p "$BUNDLE_OUTPUT_DIR"
  echo "Building bundle for Python $py_version using $py_exe..."
  "$_PY" "$SRCROOT/../scripts/build_bundle.py" \
    --python-version "$py_version" \
    --deps-hash "$PY_HASH" \
    --output-dir "$BUNDLE_OUTPUT_DIR" \
    --wheel-cache-dir "$BUNDLE_CACHE_DIR/wheels"
  for tgz in "$BUNDLE_OUTPUT_DIR"/*.tar.gz; do
    [ -f "$tgz" ] && cp "$tgz" "$BUNDLE_RESOURCES_DIR/"
  done
done < <(discover_pythons "$MIN_MINOR")
