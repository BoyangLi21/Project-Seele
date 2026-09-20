#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
test -f libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt || { echo 'Run bash install-server.sh first'; exit 1; }
test -f SEELE_TV_WORLD_PREVIEW_20260906/r26_ready.json || { echo 'Import the R26 world first'; exit 1; }
seele_java="${JAVA_HOME:+$JAVA_HOME/bin/}java"
exec "$seele_java" @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.4.10/unix_args.txt nogui
