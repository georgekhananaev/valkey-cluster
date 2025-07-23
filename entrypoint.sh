#!/bin/bash
set -e

# Function to start the Valkey cluster
start_cluster() {
    echo "Starting Valkey cluster..."
    
    # Create node directories
    for port in {6000..6005}; do
        mkdir -p /data/node-$port
    done
    
    # Start Valkey instances
    for port in {6000..6005}; do
        valkey-server /valkey-cluster/valkey.conf \
            --port $port \
            --cluster-enabled yes \
            --cluster-config-file /data/node-$port/nodes.conf \
            --cluster-node-timeout 5000 \
            --appendonly yes \
            --appendfilename appendonly-$port.aof \
            --dbfilename dump-$port.rdb \
            --logfile /data/node-$port/valkey.log \
            --dir /data/node-$port/ &
    done
    
    # Wait for all nodes to start
    echo "Waiting for nodes to start..."
    sleep 5
    
    # Check if cluster is already created
    if valkey-cli -h 127.0.0.1 -p 6000 cluster info 2>/dev/null | grep -q "cluster_state:ok"; then
        echo "Cluster already exists and is running"
    else
        echo "Creating cluster..."
        yes yes | valkey-cli --cluster create \
            127.0.0.1:6000 127.0.0.1:6001 127.0.0.1:6002 \
            127.0.0.1:6003 127.0.0.1:6004 127.0.0.1:6005 \
            --cluster-replicas 1
    fi
    
    echo "Valkey cluster is ready!"
    echo "Master nodes: 6000, 6001, 6002"
    echo "Replica nodes: 6003, 6004, 6005"
    
    # Keep container running
    tail -f /dev/null
}

# Function to run benchmarks
run_benchmark() {
    echo "Running Valkey cluster benchmark..."
    cd /valkey-cluster
    python3 test_valkey_cluster.py
}

# Function to show cluster status
show_status() {
    echo "Cluster status:"
    valkey-cli -h 127.0.0.1 -p 6000 cluster info
    echo -e "\nCluster nodes:"
    valkey-cli -h 127.0.0.1 -p 6000 cluster nodes
}

# Main logic
case "$1" in
    "cluster")
        start_cluster
        ;;
    "benchmark")
        run_benchmark
        ;;
    "status")
        show_status
        ;;
    "bash")
        /bin/bash
        ;;
    *)
        echo "Usage: $0 {cluster|benchmark|status|bash}"
        echo "  cluster    - Start the Valkey cluster"
        echo "  benchmark  - Run performance benchmarks"
        echo "  status     - Show cluster status"
        echo "  bash       - Start a bash shell"
        exit 1
        ;;
esac