#!/usr/bin/env python3
"""
Resource monitoring script that can run in container or monitor host
- Enhanced with per-process monitoring for CPU and Memory.
- Logging format is controlled by the LOG_FORMAT environment variable (log, csv, or both).
"""
import psutil
import time
import os
import subprocess
import logging
import csv
import json 
from datetime import datetime
from logging.handlers import RotatingFileHandler
from io import StringIO

# --- Configuration ---
LOG_DIR = os.getenv('LOG_DIR', '/var/log/monitor')
PROCESS_COUNT = int(os.getenv('PROCESS_COUNT', '5')) # Top N processes to monitor
# New variable to control logging format (log, csv, or both). Default to 'both'
LOG_FORMAT = os.getenv('LOG_FORMAT', 'both').lower() 

# --- Logging Setup ---

def setup_logging(mode):
    """Setup logging with rotation, conditionally creating flat and/or CSV handlers based on LOG_FORMAT"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Determine which formats to enable
    should_log = LOG_FORMAT in ['log', 'both']
    should_csv = LOG_FORMAT in ['csv', 'both']

    # Custom CSV Formatter (Unchanged)
    class CSVFormatter(logging.Formatter):
        def __init__(self, fields):
            super().__init__()
            self.fields = fields
            
        def format(self, record):
            output = StringIO()
            writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
            
            data = [
                datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S'),
                record.levelname
            ]
            
            if isinstance(record.msg, dict):
                for field in self.fields[2:]: 
                    value = record.msg.get(field, 'N/A')
                    # Complex data (lists/dicts) are JSON-encoded for a single CSV cell
                    if isinstance(value, (list, dict)):
                        data.append(json.dumps(value))
                    else:
                        data.append(value)
            else:
                data.append(record.msg)

            writer.writerow(data)
            return output.getvalue().strip()

    # Define fields for each log type
    log_fields = {
        'main': ['timestamp', 'level', 'message'],
        'cpu': ['timestamp', 'level', 'cpu_percent', 'cpu_count', 'per_cpu', 'top_processes'],
        'memory': ['timestamp', 'level', 'total_gb', 'used_gb', 'available_gb', 'percent', 'top_processes'],
        'disk': ['timestamp', 'level', 'read_mb', 'write_mb', 'read_count', 'write_count', 'per_disk_io'],
        'network': ['timestamp', 'level', 'sent_mb', 'recv_mb', 'packets_sent', 'packets_recv', 'ping_status', 'ping_latency', 'ping_host'],
    }
    
    loggers = {}
    
    for name in log_fields:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # --- 1. Flat File (.log) Handler ---
        if should_log:
            flat_filename = f'{LOG_DIR}/{name}-{mode}.log'
            flat_handler = RotatingFileHandler(
                flat_filename,
                maxBytes=10*1024*1024,
                backupCount=5
            )
            # Main logger uses standard format, others just log the raw dictionary
            flat_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s') if name == 'main' else logging.Formatter('%(asctime)s - %(message)s')
                
            flat_handler.setFormatter(flat_formatter)
            logger.addHandler(flat_handler)

        # --- 2. CSV File (.csv) Handler ---
        # Note: 'main' log is not suitable for structured CSV, so we skip it here.
        if should_csv and name != 'main': 
            csv_filename = f'{LOG_DIR}/{name}-{mode}.csv'
            csv_handler = RotatingFileHandler(
                csv_filename,
                maxBytes=10*1024*1024,
                backupCount=5
            )
            
            # Write header if file is new or empty
            if not os.path.exists(csv_filename) or os.path.getsize(csv_filename) == 0:
                header = ','.join(log_fields[name]) + '\n'
                with open(csv_filename, 'w') as f:
                    f.write(header)
                    
            csv_formatter = CSVFormatter(log_fields[name])
            csv_handler.setFormatter(csv_formatter)
            logger.addHandler(csv_handler)

        loggers[name] = logger
    
    # Console handler (optional)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
        loggers['main'].addHandler(console_handler)
    
    return loggers

# --- Monitoring Functions (Unchanged - they return data dictionaries) ---

def get_cpu_stats():
    cpu_percent = psutil.cpu_percent(interval=None) 
    cpu_count = psutil.cpu_count()
    top_procs = []
    for proc in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent']), 
                       key=lambda p: p.info.get('cpu_percent', 0), reverse=True)[:PROCESS_COUNT]:
        top_procs.append({'pid': proc.info.get('pid', 'N/A'),'name': proc.info.get('name', 'N/A'),'cpu_percent': proc.info.get('cpu_percent', 0.0)})
    return {'cpu_percent': cpu_percent,'cpu_count': cpu_count,'per_cpu': psutil.cpu_percent(interval=None, percpu=True),'top_processes': top_procs}

def get_memory_stats():
    mem = psutil.virtual_memory()
    top_procs = []
    for proc in sorted(psutil.process_iter(['pid', 'name', 'memory_info']), 
                       key=lambda p: p.info['memory_info'].rss if p.info.get('memory_info') else 0, reverse=True)[:PROCESS_COUNT]:
        mem_info = proc.info.get('memory_info')
        if mem_info:
            top_procs.append({'pid': proc.info['pid'],'name': proc.info['name'],'rss_mb': round(mem_info.rss / (1024**2), 2),'vms_mb': round(mem_info.vms / (1024**2), 2),'percent': round((mem_info.rss / mem.total) * 100, 2)})
    return {'total_gb': round(mem.total / (1024**3), 2),'used_gb': round(mem.used / (1024**3), 2),'available_gb': round(mem.available / (1024**3), 2),'percent': mem.percent,'top_processes': top_procs}

def get_disk_io():
    disk_io = psutil.disk_io_counters()
    per_disk_io = {}
    try:
        per_disk_counters = psutil.disk_io_counters(perdisk=True)
        for disk, io in per_disk_counters.items():
            per_disk_io[disk] = {'read_mb': round(io.read_bytes / (1024**2), 2),'write_mb': round(io.write_bytes / (1024**2), 2),'read_count': io.read_count,'write_count': io.write_count}
    except Exception:
        pass
    return {'read_mb': round(disk_io.read_bytes / (1024**2), 2),'write_mb': round(disk_io.write_bytes / (1024**2), 2),'read_count': disk_io.read_count,'write_count': disk_io.write_count,'per_disk_io': per_disk_io}

def ping_network(host='8.8.8.8'):
    try:
        result = subprocess.run(['ping', '-c', '1', '-W', '1', host], capture_output=True, text=True, timeout=2 )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'time=' in line:
                    time_ms = line.split('time=')[1].split()[0]
                    return {'status': 'success', 'latency_ms': time_ms, 'host': host}
        return {'status': 'failed', 'host': host}
    except Exception as e:
        return {'status': 'error', 'error': str(e), 'host': host}

def get_network_stats():
    net_io = psutil.net_io_counters()
    return {'sent_mb': round(net_io.bytes_sent / (1024**2), 2),'recv_mb': round(net_io.bytes_recv / (1024**2), 2),'packets_sent': net_io.packets_sent,'packets_recv': net_io.packets_recv}

# --- Main Loop ---

def main():
    """Main monitoring loop"""
    # Re-read LOG_FORMAT to ensure it's available in the main loop context
    global LOG_FORMAT 
    LOG_FORMAT = os.getenv('LOG_FORMAT', 'both').lower()
    
    mode = os.getenv('MONITOR_MODE', 'container')
    interval = int(os.getenv('MONITOR_INTERVAL', '5'))
    ping_host = os.getenv('PING_HOST', '8.8.8.8')
    
    psutil.cpu_percent(interval=None, percpu=True)
    psutil.disk_io_counters()
    
    loggers = setup_logging(mode)
    
    # Informational messages
    loggers['main'].info(f"Starting monitor in {mode} mode")
    loggers['main'].info(f"Logging Format Set To: {LOG_FORMAT.upper()}")
    loggers['main'].info(f"CSV Logging: {'ENABLED' if LOG_FORMAT in ['csv', 'both'] else 'DISABLED'}")
    loggers['main'].info(f"Flat Logging: {'ENABLED' if LOG_FORMAT in ['log', 'both'] else 'DISABLED'}")
    loggers['main'].info("-" * 80)
    
    print(f"Starting monitor in {mode} mode")
    print(f"Logging Format Set To: {LOG_FORMAT.upper()}")
    print("-" * 80)
    
    while True:
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # --- Get All Stats ---
            cpu = get_cpu_stats()
            mem = get_memory_stats()
            disk = get_disk_io()
            net = get_network_stats()
            ping = ping_network(ping_host)
            
            # --- Logging ---
            # All stats are logged as dictionaries. The handlers decide the output format.
            loggers['cpu'].info({
                'cpu_percent': cpu['cpu_percent'], 'cpu_count': cpu['cpu_count'], 'per_cpu': cpu['per_cpu'],'top_processes': cpu['top_processes']
            })
            loggers['memory'].info({
                'total_gb': mem['total_gb'],'used_gb': mem['used_gb'],'available_gb': mem['available_gb'],'percent': mem['percent'],'top_processes': mem['top_processes']
            })
            loggers['disk'].info({
                'read_mb': disk['read_mb'],'write_mb': disk['write_mb'],'read_count': disk['read_count'],'write_count': disk['write_count'],'per_disk_io': disk['per_disk_io']
            })
            loggers['network'].info({
                'sent_mb': net['sent_mb'], 'recv_mb': net['recv_mb'], 'packets_sent': net['packets_sent'], 'packets_recv': net['packets_recv'],'ping_status': ping['status'],'ping_latency': ping.get('latency_ms', 'N/A'),'ping_host': ping_host
            })
            
            # --- Main Log/Console Output (Summary) ---
            cpu_summary = f"CPU Usage: {cpu['cpu_percent']}% | Cores: {cpu['cpu_count']} | Top {PROCESS_COUNT}: {cpu['top_processes'][0]['name']} ({cpu['top_processes'][0]['cpu_percent']}%)"
            mem_summary = f"Memory: {mem['used_gb']}/{mem['total_gb']} GB | {mem['percent']}% | Available: {mem['available_gb']} GB | Top {PROCESS_COUNT}: {mem['top_processes'][0]['name']} ({mem['top_processes'][0]['percent']}%)"
            disk_summary = f"Disk I/O: Read {disk['read_mb']} MB ({disk['read_count']} ops) | Write {disk['write_mb']} MB ({disk['write_count']} ops)"
            net_summary = f"Network: Sent {net['sent_mb']} MB ({net['packets_sent']} pkts) | Recv {net['recv_mb']} MB ({net['packets_recv']} pkts)"
            ping_summary = f"Ping to {ping['host']}: {ping.get('latency_ms', ping['status'])} ms - {ping['status'].upper()}"
            
            loggers['main'].info(cpu_summary)
            loggers['main'].info(mem_summary)
            loggers['main'].info(disk_summary)
            loggers['main'].info(net_summary)
            loggers['main'].info(ping_summary)
            
            if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                print(f"[{timestamp}] {cpu_summary}")
                print(f"[{timestamp}] {mem_summary}")
                print(f"[{timestamp}] {disk_summary}")
                print(f"[{timestamp}] {net_summary}")
                print(f"[{timestamp}] {ping_summary}")
                print("-" * 80)
            
        except Exception as e:
            error_msg = f"Error in monitoring loop: {e}"
            loggers['main'].error(error_msg)
            print(f"ERROR: {error_msg}")
        
        time.sleep(interval)

if __name__ == "__main__":
    main()