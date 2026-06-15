import json
import os
from datetime import datetime

import psutil

OUTPUT_DIR = os.path.join("reporte", "output")


def capturar_memoria():
    """Recoge el consumo de RAM y memoria virtual del servidor."""
    memoria = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "memoria": {
            "total_gb": round(memoria.total / (1024 ** 3), 2),
            "usada_gb": round(memoria.used / (1024 ** 3), 2),
            "disponible_gb": round(memoria.available / (1024 ** 3), 2),
            "porcentaje": memoria.percent,
        },
        "swap": {
            "total_gb": round(swap.total / (1024 ** 3), 2),
            "usada_gb": round(swap.used / (1024 ** 3), 2),
            "libre_gb": round(swap.free / (1024 ** 3), 2),
            "porcentaje": swap.percent,
        },
    }


def guardar_reporte_memoria(ruta=None):
    """Guarda el consumo de memoria en un archivo JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if ruta is None:
        ruta = os.path.join(OUTPUT_DIR, "memoria_monitor.json")

    datos = capturar_memoria()
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2, ensure_ascii=False)

    return {"ruta": ruta, "datos": datos}
