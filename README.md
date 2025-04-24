# Valkey Cluster Development Setup

![Valkey Logo](https://raw.githubusercontent.com/valkey-io/valkey/master/docs/images/valkey-color-1-1.svg)

A lightweight Docker setup for spawning a multi-node Valkey cluster on your local machine. Perfect for development, testing, and benchmarking without the overhead of a full distributed deployment. This project is specifically designed to imitate AWS Valkey/ElastiCache Redis clusters locally for development purposes.

## What is Valkey?

Valkey is a high-performance, Redis-compatible, in-memory database that maintains full compatibility with the Redis protocol, clients, and modules. This project provides an easy way to set up a 6-node Valkey cluster in a single Docker container for development purposes.

## AWS Valkey Local Development

This project was created to simulate an AWS Valkey/ElastiCache Redis cluster in a local development environment. It allows developers to:

- Test applications against a cluster configuration identical to AWS deployments
- Develop and debug code locally before deploying to production AWS environments
- Benchmark performance and test application behavior without incurring AWS costs
- Practice cluster management operations safely in a local environment

## Quick Start

Clone the repo and run the cluster in three simple steps:

```bash
# 1. Create the config file
echo "protected-mode no
daemonize yes
cluster-enabled yes" > valkey.conf

# 2. Start the cluster
./start_valkey_cluster.sh

# 3. Verify it's working
./test_valkey_cluster.py
```

That's it! You now have a fully functional 6-node Valkey cluster running on ports 6000-6005.

## Advanced Benchmarking

Want to put your cluster through its paces? Run the included benchmark tool:

```bash
./benchmark_valkey_cluster.py
```

This will run a comprehensive suite of performance tests:

- Basic operations (SET/GET) in single and batch modes
- Large object storage (10 x 50MB files)
- Multi-connection throughput testing
- Maximum performance stress testing with parallel operations
- Memory usage monitoring

Results are saved as both pretty charts and detailed JSON in the `benchmarks/` directory, which is automatically created during the benchmark process.

## Features

- **AWS-like environment**: Simulates AWS Valkey/ElastiCache Redis cluster architecture locally
- **Single-container deployment**: Runs 6 Valkey nodes in just one Docker container
- **Auto-configuration**: Automatically creates a cluster with all nodes
- **Persistent storage**: Data persists between restarts in `./valkey-data/`
- **Battle-tested**: Includes comprehensive tests to verify functionality
- **Performance analysis**: Detailed benchmarking tools to measure throughput

## System Requirements

- Docker
- Python 3.6+
- 500MB free RAM (minimum)
- 1GB+ free disk space

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Valkey Cluster

```bash
chmod +x start_valkey_cluster.sh
./start_valkey_cluster.sh
```

The script will:
- Set up the directory structure
- Launch a Docker container with 6 Valkey nodes
- Configure them as a cluster
- Show connection details when ready

### 3. Test and Benchmark

```bash
# Run basic tests
chmod +x test_valkey_cluster.py
./test_valkey_cluster.py

# Run performance benchmarks
chmod +x benchmark_valkey_cluster.py
./benchmark_valkey_cluster.py
```

## Cluster Management

### Viewing Logs

```bash
docker logs -f valkey-cluster
```

### Connecting to the Cluster

Using redis-cli:
```bash
redis-cli -p 6000
```

In your application code:
```python
from redis.cluster import RedisCluster

startup_nodes = [{"host": "127.0.0.1", "port": 6000}]
rc = RedisCluster(startup_nodes=startup_nodes, decode_responses=True)
```

### Checking Cluster Status

```bash
redis-cli -p 6000 cluster info
redis-cli -p 6000 cluster nodes
```

### Stopping and Restarting

```bash
# Stop
docker stop valkey-cluster

# Start
docker start valkey-cluster
```

## Benchmark Results

The benchmarking tool generates detailed performance metrics:

- Operations per second for basic commands
- Throughput for large object storage
- Maximum concurrent connections performance
- Memory usage statistics

Example benchmark output:
```
Basic Operations:
  • SET (single): 8,500.25 ops/sec
  • SET (pipeline): 112,382.45 ops/sec
  • GET (single): 9,850.78 ops/sec
  • GET (pipeline): 186,420.32 ops/sec

Large Files:
  • Large Files Write (MB/s): 58.32 MB/sec
  • Large Files Read (MB/s): 75.45 MB/sec
```

## AWS vs Local Development Differences

While this project aims to simulate AWS Valkey as closely as possible, be aware of these differences:

- Single host deployment vs. multi-host in AWS
- No network latency between nodes compared to AWS
- No automatic failover handling as in AWS ElastiCache
- Limited to 6 nodes instead of the larger clusters possible in AWS
- No encryption in transit/at rest features

## Limitations

This setup is designed for development and testing only:

- No replication (replica count is 0)
- Single host deployment
- Not suitable for production workloads

## License

MIT License - See the [LICENSE](LICENSE) file for details.

## Author

Created by George Khananaev

---

*Note: Valkey is fully compatible with Redis clients. If you're familiar with Redis, you'll feel right at home with Valkey.*

## Cluster Details

- All nodes run in a single Docker container
- Ports: 6000-6005 mapped to localhost
- Data is persisted in `./valkey-data/`
- Each node has its own configuration and log files

## Common Commands

View logs:
```bash
docker logs -f valkey-cluster
```

Connect to a specific node:
```bash
redis-cli -p 6000
```

Check cluster status:
```bash
redis-cli -p 6000 cluster info
```

Stop the cluster:
```bash
docker stop valkey-cluster
```

Restart the cluster:
```bash
docker start valkey-cluster
```

## Notes

- This is for development purposes only and not recommended for production
- The cluster has no replicas (replica count is set to 0)
- All data is stored locally in the `valkey-data` directory