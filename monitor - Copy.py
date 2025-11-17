#!/usr/bin/env python3
"""
Resource monitoring script that can run in container or monitor host
"""
import psutil
import time
import os
import subprocess
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

def setup_logging(mode):
    """Setup logging with rotation for different log types"""
    log_dir = os.getenv('LOG_DIR', '/var/log/monitor')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create loggers for different categories
    loggers = {}
    
    # Main logger (all events)
    main_logger = logging.getLogger('main')
    main_logger.setLevel(logging.INFO)
    main_handler = RotatingFileHandler(
        f'{log_dir}/monitor-{mode}.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    main_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    main_logger.addHandler(main_handler)
    loggers['main'] = main_logger
    
    # CPU logger
    cpu_logger = logging.getLogger('cpu')
    cpu_logger.setLevel(logging.INFO)
    cpu_handler = RotatingFileHandler(
        f'{log_dir}/cpu-{mode}.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    cpu_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    cpu_logger.addHandler(cpu_handler)
    loggers['cpu'] = cpu_logger
    
    # Memory logger
    mem_logger = logging.getLogger('memory')
    mem_logger.setLevel(logging.INFO)
    mem_handler = RotatingFileHandler(
        f'{log_dir}/memory-{mode}.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    mem_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    mem_logger.addHandler(mem_handler)
    loggers['memory'] = mem_logger
    
    # Disk I/O logger
    disk_logger = logging.getLogger('disk')
    disk_logger.setLevel(logging.INFO)
    disk_handler = RotatingFileHandler(
        f'{log_dir}/disk-{mode}.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    disk_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    disk_logger.addHandler(disk_handler)
    loggers['disk'] = disk_logger
    
    # Network logger
    net_logger = logging.getLogger('network')
    net_logger.setLevel(logging.INFO)
    net_handler = RotatingFileHandler(
        f'{log_dir}/network-{mode}.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    net_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    net_logger.addHandler(net_handler)
    loggers['network'] = net_logger
    
    # Console handler (optional, for debugging)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(message)s'
    ))
    
    # Add console handler to main logger if CONSOLE_OUTPUT is enabled
    if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
        main_logger.addHandler(console_handler)
    
    return loggers

def get_cpu_stats():
    """Get CPU usage statistics"""
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count()
    return {
        'percent': cpu_percent,
        'count': cpu_count,
        'per_cpu': psutil.cpu_percent(interval=1, percpu=True)
    }

def get_memory_stats():
    """Get memory usage statistics"""
    mem = psutil.virtual_memory()
    return {
        'total_gb': round(mem.total / (1024**3), 2),
        'used_gb': round(mem.used / (1024**3), 2),
        'available_gb': round(mem.available / (1024**3), 2),
        'percent': mem.percent
    }

def get_disk_io():
    """Get disk I/O statistics"""
    disk_io = psutil.disk_io_counters()
    return {
        'read_mb': round(disk_io.read_bytes / (1024**2), 2),
        'write_mb': round(disk_io.write_bytes / (1024**2), 2),
        'read_count': disk_io.read_count,
        'write_count': disk_io.write_count
    }

def ping_network(host='8.8.8.8'):
    """Ping a network host"""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', '2', host],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            # Extract time from ping output
            for line in result.stdout.split('\n'):
                if 'time=' in line:
                    time_ms = line.split('time=')[1].split()[0]
                    return {'status': 'success', 'latency_ms': time_ms, 'host': host}
        return {'status': 'failed', 'host': host}
    except Exception as e:
        return {'status': 'error', 'error': str(e), 'host': host}

def get_network_stats():
    """Get network I/O statistics"""
    net_io = psutil.net_io_counters()
    return {
        'sent_mb': round(net_io.bytes_sent / (1024**2), 2),
        'recv_mb': round(net_io.bytes_recv / (1024**2), 2),
        'packets_sent': net_io.packets_sent,
        'packets_recv': net_io.packets_recv
    }

def main():
    """Main monitoring loop"""
    mode = os.getenv('MONITOR_MODE', 'container')
    interval = int(os.getenv('MONITOR_INTERVAL', '5'))
    ping_host = os.getenv('PING_HOST', '8.8.8.8')
    
    # Setup logging
    loggers = setup_logging(mode)
    
    loggers['main'].info(f"Starting monitor in {mode} mode")
    loggers['main'].info(f"Monitoring interval: {interval} seconds")
    loggers['main'].info(f"Ping target: {ping_host}")
    loggers['main'].info("-" * 60)
    
    print(f"Starting monitor in {mode} mode")
    print(f"Monitoring interval: {interval} seconds")
    print(f"Ping target: {ping_host}")
    print(f"Logs directory: {os.getenv('LOG_DIR', '/var/log/monitor')}")
    print("-" * 60)
    
    while True:
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # CPU Stats
            cpu = get_cpu_stats()
            cpu_msg = f"CPU Usage: {cpu['percent']}% | Cores: {cpu['count']} | Per-Core: {cpu['per_cpu']}"
            loggers['cpu'].info(cpu_msg)
            loggers['main'].info(cpu_msg)
            if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                print(f"[{timestamp}] {cpu_msg}")
            
            # Memory Stats
            mem = get_memory_stats()
            mem_msg = f"Memory: {mem['used_gb']}/{mem['total_gb']} GB | {mem['percent']}% | Available: {mem['available_gb']} GB"
            loggers['memory'].info(mem_msg)
            loggers['main'].info(mem_msg)
            if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                print(f"[{timestamp}] {mem_msg}")
            
            # Disk I/O
            try:
                disk = get_disk_io()
                disk_msg = f"Disk I/O: Read {disk['read_mb']} MB ({disk['read_count']} ops) | Write {disk['write_mb']} MB ({disk['write_count']} ops)"
                loggers['disk'].info(disk_msg)
                loggers['main'].info(disk_msg)
                if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                    print(f"[{timestamp}] {disk_msg}")
            except Exception as e:
                error_msg = f"Disk I/O: Error - {e}"
                loggers['disk'].error(error_msg)
                loggers['main'].error(error_msg)
            
            # Network Stats
            net = get_network_stats()
            net_msg = f"Network: Sent {net['sent_mb']} MB ({net['packets_sent']} pkts) | Recv {net['recv_mb']} MB ({net['packets_recv']} pkts)"
            loggers['network'].info(net_msg)
            loggers['main'].info(net_msg)
            if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                print(f"[{timestamp}] {net_msg}")
            
            # Ping Test
            ping = ping_network(ping_host)
            if ping['status'] == 'success':
                ping_msg = f"Ping to {ping['host']}: {ping['latency_ms']} ms - SUCCESS"
                loggers['network'].info(ping_msg)
                loggers['main'].info(ping_msg)
                if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                    print(f"[{timestamp}] {ping_msg}")
            else:
                ping_msg = f"Ping to {ping['host']}: {ping['status']}"
                loggers['network'].warning(ping_msg)
                loggers['main'].warning(ping_msg)
                if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                    print(f"[{timestamp}] {ping_msg}")
            
            if os.getenv('CONSOLE_OUTPUT', 'true').lower() == 'true':
                print("-" * 60)
            
        except Exception as e:
            error_msg = f"Error in monitoring loop: {e}"
            loggers['main'].error(error_msg)
            print(f"ERROR: {error_msg}")
        
        time.sleep(interval)

if __name__ == "__main__":
    main()