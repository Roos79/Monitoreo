import json
import os
from datetime import datetime

import psutil

OUTPUT_DIR = os.path.join("reporte", "output")


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
        except PermissionError:
            continue

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cpu_porcentaje": psutil.cpu_percent(interval=0.1),
        "particiones": particiones,
    }


def guardar_reporte_cpu(ruta=None):
    """Guarda el estado de CPU y particiones en un archivo JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if ruta is None:
        ruta = os.path.join(OUTPUT_DIR, "cpu_monitor.json")

    datos = capturar_particiones()
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)

    return {"ruta": ruta, "datos": datos}
