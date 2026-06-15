import json
import os
from datetime import datetime
import psutil

# Cambiado a ruta absoluta para evitar fallos con cron en producción
OUTPUT_DIR = "/opt/eir/reportes/output"

def capturar_particiones():
    """Recoge el estado de las particiones y el consumo de CPU."""
    particiones = []
    for particion in psutil.disk_partitions(all=False):
        try:
            uso = psutil.disk_usage(particion.mountpoint)
            particiones.append(
                {
                    "dispositivo": particion.device,
                    "punto_montaje": particion.mountpoint,
                    "tipo": particion.fstype,
                    "total_gb": round(uso.total / (1024 ** 3), 2),
                    "usado_gb": round(uso.used / (1024 ** 3), 2),
                    "libre_gb": round(uso.free / (1024 ** 3), 2),
                    "porcentaje": round((uso.used / uso.total) * 100, 2),
                }
            )
        except (PermissionError, FileNotFoundError):
            # En producción omitimos si no hay permisos o si es un montaje efímero desaparecido
            continue

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        # Intervalo cambiado a 1.0 para una medición más estable en servidores estresados
        "cpu_porcentaje": psutil.cpu_percent(interval=1.0),
        "particiones": particiones,
    }

def guardar_reporte_cpu(ruta=None):
    """Guarda el estado de CPU y particiones en un archivo JSON."""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except PermissionError:
        print(f"Error: No hay permisos para crear el directorio {OUTPUT_DIR}")
        return None

    if ruta is None:
        ruta = os.path.join(OUTPUT_DIR, "cpu_monitor.json")

    datos = capturar_particiones()
    try:
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, indent=2, ensure_ascii=False)
    except PermissionError:
        print(f"Error: No hay permisos para escribir en {ruta}")
        return None

    return {"ruta": ruta, "datos": datos}