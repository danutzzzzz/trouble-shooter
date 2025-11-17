FROM python:3.11-slim

# Install system dependencies for network tools and psutil
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    iputils-ping \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir psutil

# Create app directory
WORKDIR /app

# Copy the monitoring script
COPY monitor.py /app/monitor.py

# Make script executable
RUN chmod +x /app/monitor.py

# Set default environment variables
ENV MONITOR_MODE=container
ENV MONITOR_INTERVAL=5
ENV PING_HOST=8.8.8.8

# Run the monitor script
CMD ["python", "/app/monitor.py"]