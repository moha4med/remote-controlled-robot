import psutil
import time


def get_system_metrics():
    """Gather basic system metrics."""
    cpu_usage = psutil.cpu_percent(interval=0.5)
    mem_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage("/").percent
    cpu_temp = get_cpu_temp()
    uptime = int(time.time() - psutil.boot_time())

    return {
        "cpu_usage": cpu_usage,
        "memory_usage": mem_usage,
        "disk_usage": disk_usage,
        "cpu_temperature": cpu_temp,
        "uptime": uptime,
    }


def get_cpu_temp():
    """Read the CPU temperature from the system."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_str = f.read().strip()
            return round(int(temp_str) / 1000, 1)
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")
        return None