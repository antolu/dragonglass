#!/bin/sh
set -e

find_python() {
  for p in "$HOME/.conda/bin/python3" "/opt/homebrew/bin/python3" "/usr/local/bin/python3" "python3"; do
    if command -v "$p" >/dev/null 2>&1; then
      if "$p" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)"; then
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

FORCED_PYTHON="$(find_python || true)"
if [ -z "$FORCED_PYTHON" ]; then
  echo "Error: Could not find Python 3.11+" >&2
  exit 1
fi

# Xcode app builds run with a minimal PATH.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

_PY="$FORCED_PYTHON"
RESOURCES_DIR="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"
WHEELS_DIR="$RESOURCES_DIR/wheels"
CACHE_DIR="$SRCROOT/../build/python_wheels"
mkdir -p "$CACHE_DIR" "$RESOURCES_DIR"

# 1) Populate/update wheel cache.
"$_PY" -c "import subprocess, sys, tomllib; d=tomllib.load(open('$SRCROOT/../pyproject.toml', 'rb')); build_reqs=d['build-system']['requires']; subprocess.run([sys.executable, '-m', 'pip', 'download', '$SRCROOT/../'] + build_reqs + ['--dest', '$CACHE_DIR', '--exists-action', 'i'], check=True)" || echo "Offline or download failed, using cached wheels"

# 2) Build wheel bundle for app resources.
rm -rf "$WHEELS_DIR"
mkdir -p "$WHEELS_DIR"
"$_PY" -m pip wheel "$SRCROOT/../" \
  --wheel-dir "$WHEELS_DIR" \
  --no-index \
  --find-links "$CACHE_DIR"

VERSION="$("$_PY" -c "import sys; sys.path.insert(0, '$SRCROOT/../'); from dragonglass._version import version; print(version)")"
printf "%s\n" "$VERSION" > "$RESOURCES_DIR/version.txt"
"$_PY" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" > "$RESOURCES_DIR/python_version.txt"

cp "$SRCROOT/opencode/package.json" "$RESOURCES_DIR/opencode_package.json"

# 3) Build and bundle Obsidian plugin.
PLUGIN_DIR="$SRCROOT/../obsidian-plugin"
PLUGIN_RES_DIR="$RESOURCES_DIR/ObsidianPlugin"
mkdir -p "$PLUGIN_RES_DIR"

if [ ! -d "$PLUGIN_DIR" ]; then
  echo "Error: obsidian-plugin directory not found at $PLUGIN_DIR" >&2
  exit 1
fi

PNPM_RUNNER="$(find_pnpm_runner || true)"
if [ -z "$PNPM_RUNNER" ]; then
  echo "Error: Could not find pnpm/corepack in Xcode build environment." >&2
  echo "PATH=$PATH" >&2
  echo "Fix options:" >&2
  echo "  1) Install Node.js: brew install node" >&2
  echo "  2) Enable pnpm: corepack enable && corepack prepare pnpm@latest --activate" >&2
  echo "  3) Restart Xcode after installing node/pnpm" >&2
  echo "  4) Verify in Terminal: which pnpm (or which corepack)" >&2
  exit 1
fi

(
  cd "$PLUGIN_DIR"
  # shellcheck disable=SC2086
  $PNPM_RUNNER install --frozen-lockfile
  # shellcheck disable=SC2086
  $PNPM_RUNNER build
)

cp "$PLUGIN_DIR/main.js" "$PLUGIN_RES_DIR/main.js"
cp "$PLUGIN_DIR/manifest.json" "$PLUGIN_RES_DIR/manifest.json"
