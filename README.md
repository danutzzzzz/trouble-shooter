\# Docker Resource Monitoring Setup



This setup provides two monitoring scenarios with comprehensive logging:

1\. \*\*Container monitoring\*\*: Monitors the container's own resources

2\. \*\*Host monitoring\*\*: Monitors the host system from within a container



\## File Structure

```

.

├── Dockerfile

├── docker-compose.yml

├── monitor.py

└── logs/                    # Created automatically

&nbsp;   ├── container/           # Container monitoring logs

&nbsp;   │   ├── monitor-container.log

&nbsp;   │   ├── cpu-container.log

&nbsp;   │   ├── memory-container.log

&nbsp;   │   ├── disk-container.log

&nbsp;   │   └── network-container.log

&nbsp;   └── host/                # Host monitoring logs

&nbsp;       ├── monitor-host.log

&nbsp;       ├── cpu-host.log

&nbsp;       ├── memory-host.log

&nbsp;       ├── disk-host.log

&nbsp;       └── network-host.log

```



\## Logging Features



\### Log Files Generated

Each monitoring mode creates \*\*5 log files\*\*:



1\. \*\*monitor-{mode}.log\*\* - All events (combined)

2\. \*\*cpu-{mode}.log\*\* - CPU usage metrics

3\. \*\*memory-{mode}.log\*\* - Memory usage metrics

4\. \*\*disk-{mode}.log\*\* - Disk I/O statistics

5\. \*\*network-{mode}.log\*\* - Network stats and ping results



\### Log Rotation

\- Maximum file size: \*\*10MB\*\*

\- Backup files kept: \*\*5\*\* (total 50MB per log type)

\- Automatic rotation when size limit reached



\### Log Format

```

2025-11-17 10:30:45 - INFO - CPU Usage: 25.3% | Cores: 8 | Per-Core: \[22.1, 28.5, ...]

2025-11-17 10:30:45 - INFO - Memory: 4.2/16.0 GB | 26.3% | Available: 11.8 GB

```



\## Setup Instructions



\### 1. Save all files

Save the three files (`Dockerfile`, `docker-compose.yml`, and `monitor.py`) in the same directory.



\### 2. Build and Run



\#### Option A: Run both scenarios

```bash

docker-compose up --build

```



\#### Option B: Run only container monitoring

```bash

docker-compose up --build monitor-container

```



\#### Option C: Run only host monitoring

```bash

docker-compose up --build monitor-host

```



\### 3. Run in detached mode (background)

```bash

docker-compose up -d --build

```



\### 4. View logs



\*\*View container logs (Docker output):\*\*

```bash

\# View all logs

docker-compose logs -f



\# View specific service logs

docker-compose logs -f monitor-host

docker-compose logs -f monitor-container

```



\*\*View persistent log files:\*\*

```bash

\# View all events for host monitoring

tail -f logs/host/monitor-host.log



\# View CPU logs

tail -f logs/host/cpu-host.log



\# View memory logs

tail -f logs/container/memory-container.log



\# View last 100 lines of network logs

tail -n 100 logs/host/network-host.log



\# Search for errors

grep ERROR logs/host/monitor-host.log



\# Monitor all CPU logs in real-time

watch -n 1 tail -20 logs/host/cpu-host.log

```



\*\*Analyze logs with common tools:\*\*

```bash

\# Count entries per log file

wc -l logs/host/\*.log



\# Find high CPU usage entries (over 80%)

grep -E "CPU Usage: \[8-9]\[0-9]|100" logs/host/cpu-host.log



\# Find high memory usage (over 80%)

grep -E "\[8-9]\[0-9]\\.\[0-9]%|100%" logs/host/memory-host.log



\# Check ping failures

grep -i "fail\\|error" logs/host/network-host.log

```



\### 5. Stop the containers

```bash

docker-compose down

```



\## Configuration Options



You can customize the monitoring behavior by editing environment variables in `docker-compose.yml`:



\- \*\*MONITOR\_MODE\*\*: `container` or `host` (informational only)

\- \*\*MONITOR\_INTERVAL\*\*: Seconds between monitoring cycles (default: 5)

\- \*\*PING\_HOST\*\*: Host to ping for network testing (default: 8.8.8.8)

\- \*\*LOG\_DIR\*\*: Directory for log files (default: /var/log/monitor)

\- \*\*CONSOLE\_OUTPUT\*\*: Show output in console (default: true, set to false to disable)



Example:

```yaml

environment:

&nbsp; - MONITOR\_MODE=host

&nbsp; - MONITOR\_INTERVAL=10

&nbsp; - PING\_HOST=google.com

&nbsp; - CONSOLE\_OUTPUT=false  # Logs only, no console output

```



\## What Gets Monitored



\- \*\*CPU\*\*: Usage percentage and core count

\- \*\*Memory\*\*: Total, used, available (in GB and percentage)

\- \*\*Disk I/O\*\*: Read/write bytes and operation counts

\- \*\*Network\*\*: Sent/received bytes and packet counts

\- \*\*Ping\*\*: Network latency to specified host



\## Host Monitoring Explanation



The `monitor-host` service uses several Docker features to access host resources:



1\. \*\*Volume mounts\*\*: Mounts `/proc`, `/sys`, and `/etc` from host as read-only

2\. \*\*pid: host\*\*: Shares host's PID namespace

3\. \*\*network\_mode: host\*\*: Uses host's network stack

4\. \*\*privileged: true\*\*: Grants full host access (required for complete monitoring)

5\. \*\*cap\_add\*\*: Adds SYS\_PTRACE and SYS\_ADMIN capabilities



⚠️ \*\*Security Note\*\*: The host monitoring container runs in privileged mode, which grants extensive access to the host system. Only use this in trusted environments.



\## Troubleshooting



\### Permission errors

If you encounter permission errors, ensure the container is running with sufficient privileges (the compose file already sets this up).



\### Network ping fails

\- Ensure ICMP is not blocked by firewall

\- Try changing PING\_HOST to a different address

\- Check if the container has network access



\### Disk I/O errors on host monitoring

Some disk statistics may not be available depending on the host system configuration. This is normal and the script will continue monitoring other metrics.



\## Running Standalone (without Compose)



\### Build the image

```bash

docker build -t resource-monitor .

```



\### Run container monitoring

```bash

docker run --rm resource-monitor

```



\### Run host monitoring

```bash

docker run --rm \\

&nbsp; --pid=host \\

&nbsp; --network=host \\

&nbsp; --privileged \\

&nbsp; -v /proc:/host/proc:ro \\

&nbsp; -v /sys:/host/sys:ro \\

&nbsp; -v /etc:/host/etc:ro \\

&nbsp; -e MONITOR\_MODE=host \\

&nbsp; resource-monitor

```

