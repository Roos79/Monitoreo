#!/usr/bin/env python3

import os
import re
import psutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

UMBRAL_TPS_LTE = 570
UMBRAL_TPS_GSM = 4000
MAX_TRANSACCIONES = 10
PATRON_LINEA = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*->\s*\[(?P<valor>\d+)\]\s*$"
)
PATRON_LINEA_GSM = re.compile(
    r"^(?P<timestamp>\d{14})\s+(?P<valor>\d+)\s+(?P<control>\d+)\s*$"
)
def capturar_cpu():
    return psutil.cpu_percent(interval=1)


def capturar_memoria_free():
    # Captura la memoria RAM utilizando el comando 'free -h' en lugar de psutil.
    try:
        resultado = subprocess.run(
            ["free", "-h"], capture_output=True, text=True, check=True
        )
        return {"estado": "OK", "datos": resultado.stdout}
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        return {
            "estado": "ERROR", 
            "datos": f"Erro al ejecutar 'free -h' en el servidor: {exc}",
        }


def capturar_filesystem():
    particiones = []

    for p in psutil.disk_partitions():
        try:
            uso = psutil.disk_usage(p.mountpoint)

            particiones.append({
                "dispositivo": p.device,
                "montaje": p.mountpoint,
                "total_gb": round(uso.total / (1024**3), 2),
                "usado_gb": round(uso.used / (1024**3), 2),
                "porcentaje": uso.percent
            })

        except PermissionError:
            pass

    return particiones

def capturar_lte():
    """Captura las transacciones LTE desde el archivo de tpscontrol."""
    ruta = os.getenv("MONITOREO_LTE_PATH", "/opt/eir/var/tps/tpscontrol")
    archivo = Path(ruta)

    if not archivo.exists():
        return {"error": f"No se encontró el archivo LTE: {ruta}"}

    #Calcular el tiempo límite de corte (ahora mismo menos 1 hora)
    hora_actual = datetime.now()
    hora_corte = hora_actual - timedelta(hours=1)

    transacciones_en_hora = []
    #Lectura línea por linea secuencialmente
    with archivo.open("r", encoding="utf-8", errors="ignore") as fh:
        for linea in fh:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            coincidencia = PATRON_LINEA.match(linea_limpia)
            if not coincidencia:
                continue    
            #Extraer y parsear la fecha de la línea del log
            try:
                timestamp_log =datetime.strptime(
                    coincidencia.group("timestamp"), "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                continue
            #Filtrar solo la ultima hora de transacciones
            if timestamp_log >= hora_corte:
                transacciones_en_hora.append(
                    {
                        "timestamp": coincidencia.group("timestamp"),
                        "valor": int(coincidencia.group("valor")),
                        "linea": linea_limpia,
                    }
                )
    #Filtrar picos baándose unicamente en el grupo de la última hora de transacciones
    alertas = [
        item for item in transacciones_en_hora if item["valor"] > UMBRAL_TPS_LTE]
    pico_maximo = (max(
        transacciones_en_hora, key=lambda item: item["valor"]) if transacciones_en_hora 
        else None
    )

    return {
        "total_evaluadas": len(transacciones_en_hora),
        "umbral": UMBRAL_TPS_LTE,
        "alertas": alertas,
        "pico_maximo": pico_maximo,
        "ultimas_muestras": transacciones_en_hora[-MAX_TRANSACCIONES:],
    }
def capturar_gsm():
    """Captura las transacciones GSM desde el archivo de tpscontrol."""
    ruta = os.getenv("MONITOREO_GSM_PATH", "/opt/eir/var/stats/su1-tps-eir_stats")
    archivo = Path(ruta)

    if not archivo.exists():
        return {"error": f"No se encontró el archivo GSM: {ruta}"}

    hora_actual = datetime.now()
    hora_corte = hora_actual - timedelta(hours=1)

    transacciones_en_hora = []
    with archivo.open("r", encoding="utf-8", errors="ignore") as fh:
        for linea in fh:
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            coincidencia = PATRON_LINEA_GSM.match(linea_limpia)
            if not coincidencia:
                continue    
            try:
                timestamp_log = datetime.strptime(
                    coincidencia.group("timestamp"), "%Y%m%d%H%M%S"
                )
            except ValueError:
                continue

            if timestamp_log >= hora_corte:
                transacciones_en_hora.append(
                    {
                        "timestamp": coincidencia.group("timestamp"),
                        "valor": int(coincidencia.group("valor")),
                        "linea": linea_limpia,
                    }
                )
    alertas = [item for item in transacciones_en_hora if item["valor"] > UMBRAL_TPS_GSM]
    pico_maximo = (max(transacciones_en_hora, key=lambda item: item["valor"]) if transacciones_en_hora else None)

    return {
        "total_evaluadas": len(transacciones_en_hora),
        "umbral": UMBRAL_TPS_GSM,
        "alertas": alertas,
        "pico_maximo": pico_maximo,
        "ultimas_muestras": transacciones_en_hora[-MAX_TRANSACCIONES:],
    }


def main():

    print("=" * 60)
    print("MONITOREO DE RECURSOS")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    cpu = capturar_cpu()
    reporte_memoria = capturar_memoria_free()
    filesystem = capturar_filesystem()

    print(f"\nCPU: {cpu}%")

    print("\nMEMORIA y SWAP (free -h) de la SU 1:")
    if reporte_memoria["estado"] == "OK":
        print(reporte_memoria["datos"])
    else:
        print(f"Error al capturar memoria: {reporte_memoria['datos']}")


    print("\nFILESYSTEM")

    for fs in filesystem:
        print(
            f"{fs['montaje']} -> "
            f"{fs['porcentaje']}% "
            f"({fs['usado_gb']} GB / {fs['total_gb']} GB)"
        )

    lte = capturar_lte()
    print("\nLTE")
    if "error" in lte:
        print(f"{lte['error']}")
    else:
        print(f"Total registros en la última hora: {lte['total_evaluadas']}")
        print(f"Umbral operativo límite: > {lte['umbral']} TPS")

        if lte["alertas"]:
            print(
                f"\n ALERTA: Se detectaron {len(lte['alertas'])} picos por encima del umbral en la última hora:"
            )
            for item in lte["alertas"]:
                print(f"  - {item['timestamp']} -> [{item['valor']}] TPS")
        else:
            print(
                f"\n Sin alertas: Ninguna transacción superó los {lte['umbral']} TPS en la última hora."
            )

            # Si no hay alertas, opcionalmente te muestro un vistazo de las últimas líneas procesadas
            if lte["ultimas_muestras"]:
                print("\nVistazo a las últimas transacciones registradas:")
                for item in lte["ultimas_muestras"]:
                    print(f"  - {item['timestamp']} -> [{item['valor']}]")

        if lte["pico_maximo"]:
            print(
                "\n Pico máximo registrado en esta hora: "
                f"{lte['pico_maximo']['valor']} TPS a las "
                f"{lte['pico_maximo']['timestamp']}"
            )

    gsm = capturar_gsm()
    print("\nGSM")
    if "error" in gsm:
        print(f"{gsm['error']}")
    else:
        print(f"Total registros en la última hora: {gsm['total_evaluadas']}")
        print(f"Umbral operativo límite: > {gsm['umbral']} TPS")

        if gsm["alertas"]:
            print(
                f"\n ALERTA: Se detectaron {len(gsm['alertas'])} picos por encima del umbral en la última hora:"
            )
            for item in gsm["alertas"]:
                print(f" {item['linea']}")
                #para que salga bonito
               # print(f"  - {item['timestamp']} -> [{item['valor']}] TPS")
        else:
            print(
                f"\n Sin alertas: Ninguna transacción superó los {gsm['umbral']} TPS en la última hora."
            )

            if gsm["ultimas_muestras"]:
                print("\nVistazo a las últimas transacciones registradas:")
                for item in gsm["ultimas_muestras"]:
                    print(f" {item['linea']}")
                    #formato de lte
                    #print(f"  - {item['timestamp']} -> [{item['valor']}]")

        if gsm["pico_maximo"]:
            print(
                "\n Pico máximo registrado en esta hora: "
                f"{gsm['pico_maximo']['valor']} TPS a las "
                f"{gsm['pico_maximo']['timestamp']}"

            )
    print("\nMonitoreo finalizado")


if __name__ == "__main__":
    main()