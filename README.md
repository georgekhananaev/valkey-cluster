# Valkey Cluster Development Setup

![Valkey Logo](https://valkey.io/img/valkey-horizontal.svg)

I built this lightweight Docker setup to quickly spin up a multi-node Valkey cluster on my local machine. It's been super useful for development, testing, and benchmarking without the headache of a full distributed deployment. I specifically designed this to mimic AWS Valkey/ElastiCache Redis clusters locally for development.

## What is Valkey?

Valkey is essentially a high-performance, Redis-compatible, in-memory database. It maintains full compatibility with the Redis protocol, clients, and modules. This project gives you a dead-simple way to set up a 6-node Valkey cluster in a single Docker container for development.

## AWS Valkey Local Development

I created this project to simulate an AWS Valkey/ElastiCache Redis cluster locally. It lets you:

- Test your apps against a cluster config that matches AWS deployments
- Develop and debug code locally before pushing to production AWS environments
- Run benchmarks and test behavior without burning AWS credits
- Practice cluster management safely on your own machine

## Quick Start

Clone the repo and run the cluster in three quick steps:

```bash
# 1. Make sure you have the valkey.conf file (which you already do)

# 2. Start the cluster
./start_valkey_cluster.sh

# 3. Verify it's working
./test_valkey_cluster.py
```

That's it! You now have a fully functional 6-node Valkey cluster running on ports 6000-6005.

## Advanced Benchmarking

Want to see what your cluster can handle? Run the included benchmark tool:

```bash
./benchmark_valkey_cluster.py
```

This runs a comprehensive suite of performance tests:

- Basic operations (SET/GET) in single and batch modes
- Large object storage (single 50MB object, with optional chunking)
- Read and write performance measurement in MB/sec
- Comparison between single-value and chunked storage approaches

Results are saved as pretty charts and detailed JSON in the `benchmarks/` directory, which gets created automatically during the benchmark.

## Features

- **AWS-like environment**: Mimics AWS Valkey/ElastiCache Redis cluster architecture locally
- **Single-container deployment**: Runs 6 Valkey nodes in just one Docker container
- **Auto-configuration**: Sets up a cluster with all nodes automatically
- **Persistent storage**: Your data sticks around between restarts in `./valkey-data/`
- **Battle-tested**: Comes with solid tests to verify everything works
- **Performance analysis**: Detailed benchmarking to see how fast things run

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

The script:
- Sets up the directory structure
- Launches a Docker container with 6 Valkey nodes
- Configures them as a cluster
- Shows connection details when ready

### 3. Test and Benchmark

```bash
# Run basic tests & performance benchmarks
chmod +x test_valkey_cluster.py
./test_valkey_cluster.py
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

The benchmarking tool generates some nice performance metrics:

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

Large Object:
  • Large Write (MB/s): 58.32 MB/sec
  • Large Read (MB/s): 75.45 MB/sec
```

## AWS vs Local Development Differences

While I've tried to make this mimic AWS Valkey as closely as possible, here are the key differences:

- Single host deployment vs. multi-host in AWS
- No network latency between nodes compared to AWS
- No automatic failover handling like in AWS ElastiCache
- Limited to 6 nodes instead of the larger clusters possible in AWS
- No encryption in transit/at rest features

## Limitations

This setup is meant for development and testing only:

- No replication (replica count is 0)
- Single host deployment
- Not suitable for production workloads

## License

MIT License - See the [LICENSE](LICENSE) file for details.

## Author

Created by George Khananaev

---

*Note: Valkey plays nicely with all Redis clients. If you know Redis, you'll feel right at home with Valkey.*

## Cluster Details

- All nodes run in a single Docker container
- Ports: 6000-6005 mapped to localhost
- Data persists in `./valkey-data/`
- Each node has its own config and log files

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

- This is for development purposes only - I wouldn't recommend it for production
- The cluster has no replicas (replica count is set to 0)
- All data is stored locally in the `valkey-data` directory