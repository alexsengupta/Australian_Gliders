#!/usr/bin/env bash
# publish.sh — upload the website files to the public object-storage container.
# Needs non-interactive OpenStack creds in ~/gliders-openrc.sh (OS_PASSWORD set).
set -euo pipefail
cd "$(dirname "$0")"
source ~/gliders-openrc.sh
CONTAINER="${GLIDERS_CONTAINER:-australian-gliders}"
swift upload "$CONTAINER" glider_map.html climatology.js deployments.js
swift upload "$CONTAINER" plotdata --changed
swift upload "$CONTAINER" assets --changed
echo "published to $CONTAINER at $(date -u)"
