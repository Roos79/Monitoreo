import argparse
import os
import re
from pathlib import Path

UMBRAL_TPS = 550
MAX_TRANSACCIONES = 10
PATRON_LINEA = re.compile(r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*->\s*\[(?P<valor>\d+)\]\s*$")


def leer_transacciones(ruta):
    """ESTADO TPS LTE deben estar en un rango de 200 a 500."""
    archivo = Path(ruta)
    if not archivo.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {ruta}")

    with open(archivo, "r", encoding="utf-8", errors="ignore") as fh:
        lineas = [linea.strip() for linea in fh if linea.strip()]

    transacciones = []
    for linea in lineas[-MAX_TRANSACCIONES:]:
        coincidencia = PATRON_LINEA.match(linea)
        if not coincidencia:
            continue

        transacciones.append(
            {
                "timestamp": coincidencia.group("timestamp"),
                "valor": int(coincidencia.group("valor")),
                "linea": linea,
            }
        )

    return transacciones


def analizar_transacciones(transacciones, umbral=UMBRAL_TPS):
    """ Picos por encima del umbral."""
    alertas = [item for item in transacciones if item["valor"] > umbral]
    pico_maximo = max(transacciones, key=lambda item: item["valor"]) if transacciones else None

    return {
        "total": len(transacciones),
        "umbral": umbral,
        "alertas": alertas,
        "pico_maximo": pico_maximo,
        "hay_picos": bool(alertas),
    }

""
def main():
    parser = argparse.ArgumentParser(description="Monitoreo de transacciones GSM ")
    parser.add_argument(
        "--ruta",
        default=os.getenv("MONITOREO_GSM_PATH", "/opt/eir/var/stats/su2-tps-eir_stats"),
        help="Ruta del archivo de transacciones GSM a monitorear.",
    )
    args = parser.parse_args()

    try:
        transacciones = leer_transacciones(args.ruta)
        resultado = analizar_transacciones(transacciones)
    except Exception as exc:
        print(f"Error al leer el archivo GSM: {exc}")
        return 1

    print(f"Transacciones GSM capturadas (últimas {resultado['total']}):")
    for item in transacciones:
        print(f"  - {item['timestamp']} -> [{item['valor']}]")

    print(f"\nUmbral configurado: > {resultado['umbral']}")

    if resultado['alertas']:
        print("\nALERTA: se detectaron transacciones por encima del umbral:")
        for item in resultado['alertas']:
            print(f"  - {item['timestamp']} -> [{item['valor']}]")
    else:
        print("\nSin alertas: ninguna transacción superó el umbral de 520.")

    if resultado['pico_maximo']:
        print(
            "\nPico máximo detectado: "
            f"{resultado['pico_maximo']['valor']} transacciones en "
            f"{resultado['pico_maximo']['timestamp']}"
        )
    else:
        print("\nNo hay datos suficientes para identificar un pico.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
