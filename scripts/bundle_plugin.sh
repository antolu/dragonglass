#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$REPO_ROOT/obsidian-plugin"
DEST_DIR="$REPO_ROOT/DragonglassApp/Resources/ObsidianPlugin"

echo "Building obsidian-vector-search-server..."
cd "$PLUGIN_DIR"
pnpm install --frozen-lockfile
pnpm run build

echo "Copying plugin artifacts to $DEST_DIR..."
mkdir -p "$DEST_DIR"
cp "$PLUGIN_DIR/main.js" "$DEST_DIR/main.js"
cp "$PLUGIN_DIR/manifest.json" "$DEST_DIR/manifest.json"

echo "Done — plugin bundled at $DEST_DIR"
