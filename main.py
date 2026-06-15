import os
from conexion import conectar_y_recolectar

def mostrar_resumen_tps(nombre, resultado):
    """Muestra en la consola local el resumen de transacciones procesadas remotamente."""
    print(f"\n[{nombre}] Monitoreo de transacciones del Servidor")
    if not resultado:
        print("- No se recibieron datos del servidor para este módulo.")
        return

    print(f"- Total transacciones evaluadas (últimas): {resultado['total']}")
    print(f"- Umbral límite: > {resultado['umbral']}")

    if resultado['alertas']:
        print("ALERTA: ¡Se detectaron picos que superan el umbral operativo!")
        for item in resultado['alertas']:
            print(f"  • {item['timestamp']} -> [{item['valor']}]")
    else:
        print("Sin alertas: Los niveles de TPS se encuentran estables.")

    if resultado['pico_maximo']:
        print(
            f" Pico máximo en la muestra: {resultado['pico_maximo']['valor']} TPS "
            f"a las {resultado['pico_maximo']['timestamp']}"
        )

def main():
    """Orquestador central del monitoreo local."""
    print("=== INICIANDO EXTRACCIÓN DE MÉTRICAS REMOTAS ===")
    
    # Realizar el salto SSH y traer los datos del servidor de producción
    datos_servidor = conectar_y_recolectar()
    
    if datos_servidor["estado"] == "ERROR":
        print(f" Error crítico: {datos_servidor['error']}")
        return

    print(f" Conectado exitosamente a: {datos_servidor['usuario']}@{datos_servidor['host']}")
    print("================================================")

    # 1. Mostrar Particiones
    if datos_servidor["cpu"]:
        print("\n[HARDWARE] Estado de Almacenamiento:")
        for particion in datos_servidor["cpu"]["particiones"]:
            print(
                f"- {particion['dispositivo']} ({particion['punto_montaje']}) -> {particion['porcentaje']}% usado "
                f"({particion['usado_gb']} GB usados de {particion['total_gb']} GB)"
            )
        print(f"- Consumo instantáneo de CPU: {datos_servidor['cpu']['cpu_porcentaje']}%")

    # 2. Mostrar Memoria
    if datos_servidor["memoria"]:
        print("\n[HARDWARE] Estado de Memoria:")
        mem = datos_servidor["memoria"]["memoria"]
        print(f"- RAM: {mem['porcentaje']}% usado ({mem['usada_gb']} GB de {mem['total_gb']} GB)")
        swap = datos_servidor["memoria"]["swap"]
        print(f"- SWAP: {swap['porcentaje']}% usado ({swap['usada_gb']} GB de {swap['total_gb']} GB)")

    # 3. Mostrar TPS de Servicios (LTE y GSM)
    mostrar_resumen_tps("LTE", datos_servidor["lte"])
    mostrar_resumen_tps("GSM", datos_servidor["gsm"])

    # 4. Sección de Diagnóstico (por si algo falló en el backend del servidor)
    errores = datos_servidor.get("errores", {})
    if any(errores.values()):
        print("\n[DIAGNÓSTICO] Avisos del sistema remoto:")
        for modulo, err_msg in errores.items():
            if err_msg:
                print(f"  • Aviso en {modulo.upper()}: {err_msg}")

    print("\n=== MONITOREO FINALIZADO ===")

if __name__ == "__main__":
    main()