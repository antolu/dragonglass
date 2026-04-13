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

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

RESOURCES_DIR="$TARGET_BUILD_DIR/$UNLOCALIZED_RESOURCES_FOLDER_PATH"
mkdir -p "$RESOURCES_DIR"

_PY="$(find_python || true)"
if [ -z "$_PY" ]; then
  echo "Error: Could not find Python 3.11+" >&2
  exit 1
fi

VERSION="$("$_PY" -c "import sys; sys.path.insert(0, '$SRCROOT/../'); from dragonglass._version import version; print(version)")"
printf "%s\n" "$VERSION" > "$RESOURCES_DIR/version.txt"

# Copy dragonglass Python source for bootstrap (needed before venv exists).
DRAGONGLASS_SRC="$SRCROOT/../dragonglass"
DRAGONGLASS_RES="$RESOURCES_DIR/dragonglass_src/dragonglass"
rm -rf "$DRAGONGLASS_RES"
cp -R "$DRAGONGLASS_SRC" "$RESOURCES_DIR/dragonglass_src/"

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
