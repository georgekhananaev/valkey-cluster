#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Spin-up a six-node Valkey cluster in ONE Docker container (ports 6000-6005).
# Re-runs safely: if the data directory already holds a healthy cluster the
# script just starts the nodes and skips the cluster-create step.
# ---------------------------------------------------------------------------
set -euo pipefail

CONTAINER="valkey-cluster"
IMAGE="valkey/valkey:7.2"
DATA_DIR="$(pwd)/valkey-data"

# ── wipe old container, keep data (makes restarts idempotent) ────────────────
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
mkdir -p "$DATA_DIR"
cp valkey.conf "$DATA_DIR/valkey.conf"

# ── launch container ────────────────────────────────────────────────────────
docker run -d --name "$CONTAINER" \
  --restart unless-stopped \
  -p 6000-6005:6000-6005 \
  -v "$DATA_DIR":/data \
  "$IMAGE" bash -c '
set -euo pipefail
CFG=/data/valkey.conf

# Start 6 instances; each gets its own nodes.conf to avoid collisions
for port in $(seq 6000 6005); do
  mkdir -p /data/node-${port}
  valkey-server "$CFG" \
      --port "$port" \
      --dir "/data/node-${port}" \
      --cluster-config-file "/data/node-${port}/nodes.conf" \
      --logfile "/data/node-${port}/valkey.log" &
done

echo "❯ Waiting for processes…" ; sleep 3

# If no cluster yet, create one (non-interactive “yes”)
if ! valkey-cli -p 6000 cluster info 2>/dev/null | grep -q "cluster_state:ok"; then
  echo "❯ Creating cluster…"
  yes yes | valkey-cli --cluster create 127.0.0.1:{6000..6005} --cluster-replicas 0
fi

# Verify health
echo "❯ Verifying cluster health…"
for i in {1..30}; do
  state=$(valkey-cli -p 6000 cluster info | grep cluster_state | cut -d: -f2)
  slots=$(valkey-cli -p 6000 cluster info | grep cluster_slots_assigned | cut -d: -f2)
  [[ "$state" == "ok" && "$slots" == "16384" ]] && break
  echo "  • state=$state slots=$slots ($i/30)" ; sleep 2
done

valkey-cli -p 6000 cluster info
echo "✔ Cluster ready – tailing logs."
tail -f /data/node-*/valkey.log
'

echo -e "\n✅  Valkey cluster → redis://localhost:6000"
echo "ℹ️   Logs: docker logs -f $CONTAINER"
