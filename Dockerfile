FROM valkey/valkey:7.2

# Install Python and required system packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create a Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /valkey-cluster

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY valkey.conf .
COPY start_valkey_cluster.sh .
COPY test_valkey_cluster.py .
COPY entrypoint.sh .

# Make scripts executable
RUN chmod +x start_valkey_cluster.sh entrypoint.sh

# Create directories for data and benchmarks
RUN mkdir -p /data /valkey-cluster/benchmarks

# Expose all Valkey ports
EXPOSE 6000 6001 6002 6003 6004 6005

# Set entrypoint
ENTRYPOINT ["/valkey-cluster/entrypoint.sh"]

# Default command starts the cluster
CMD ["cluster"]