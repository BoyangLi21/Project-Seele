#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
installer=forge-1.20.1-47.4.10-installer.jar
url=https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-installer.jar
expected=66bfea9963bfa60d88bab6b2750e74a958392715
if ! echo "$expected  $installer" | sha1sum --check --status; then
    curl --fail --location --retry 3 --user-agent 'Mozilla/5.0 Project-SEELE/26' "$url" --output "$installer.download"
    echo "$expected  $installer.download" | sha1sum --check
    mv -- "$installer.download" "$installer"
fi
seele_java="${JAVA_HOME:+$JAVA_HOME/bin/}java"
"$seele_java" -jar "$installer" --installServer
echo 'Forge installed. Import the world, review eula.txt, then bash start-server.sh.'
