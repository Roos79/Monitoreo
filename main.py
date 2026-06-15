import os

from recolectores.cpu import guardar_reporte_cpu
from recolectores.gsm import analizar_transacciones as analizar_gsm, leer_transacciones as leer_gsm
from recolectores.lte import analizar_transacciones as analizar_lte, leer_transacciones as leer_lte
from recolectores.memoria import guardar_reporte_memoria


def conectar_ssh():
    """Intenta establecer una conexión SSH al servidor usando variables de entorno."""
    host = os.getenv("MONITOREO_SSH_HOST")
    usuario = os.getenv("MONITOREO_SSH_USER")
    puerto = int(os.getenv("MONITOREO_SSH_PORT", "22"))
    clave = os.getenv("MONITOREO_SSH_KEY")

    if not host or not usuario:
        return None

    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("Falta la dependencia 'paramiko'. Instálala con pip.") from exc

    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs = {"hostname": host, "username": usuario, "port": puerto}
    if clave:
        kwargs["key_filename"] = clave

    cliente.connect(**kwargs)
    stdin, stdout, stderr = cliente.exec_command("uname -a && free -h")
    salida = stdout.read().decode("utf-8", errors="ignore")
    error = stderr.read().decode("utf-8", errors="ignore")
    cliente.close()

    return {
        "host": host,
        "usuario": usuario,
        "puerto": puerto,
        "salida": salida.strip(),
        "error": error.strip(),
    }


def mostrar_resumen_tps(nombre, ruta, leer_func, analizar_func):
    """Muestra un resumen de transacciones TPS para LTE/GSM."""
    print(f"\n[{nombre}] Monitoreo de transacciones")
    try:
        transacciones = leer_func(ruta)
        resultado = analizar_func(transacciones)

        print(f"- Ruta: {ruta}")
        print(f"- Últimas transacciones capturadas: {resultado['total']}")
        print(f"- Umbral configurado: > {resultado['umbral']}")

        if transacciones:
            print("- Muestra reciente:")
            for item in transacciones[-5:]:
                print(f"  • {item['timestamp']} -> [{item['valor']}]")

        if resultado['alertas']:
            print("- ALERTA: se detectaron picos por encima del umbral.")
            for item in resultado['alertas']:
                print(f"  • {item['timestamp']} -> [{item['valor']}]")
        else:
            print("- Sin alertas por encima del umbral.")

        if resultado['pico_maximo']:
            print(
                "- Pico máximo: "
                f"{resultado['pico_maximo']['valor']} transacciones en "
                f"{resultado['pico_maximo']['timestamp']}"
            )
    except Exception as exc:
        print(f"- No se pudo leer el archivo {nombre}: {exc}")


def main():
    """Ejecuta el monitoreo del servidor y guarda los reportes en la carpeta de salida."""
    reporte_cpu = guardar_reporte_cpu()
    reporte_memoria = guardar_reporte_memoria()

    print("Monitoreo del servidor completado.")

    print("\nResumen de particiones:")
    for particion in reporte_cpu['datos']['particiones']:
        print(
            f"- {particion['dispositivo']} -> {particion['porcentaje']}% usado "
            f"({particion['usado_gb']} GB de {particion['total_gb']} GB)"
        )

    print("\nResumen de memoria:")
    memoria = reporte_memoria['datos']['memoria']
    print(
        f"- RAM: {memoria['porcentaje']}% usado "
        f"({memoria['usada_gb']} GB de {memoria['total_gb']} GB)"
    )

    lte_path = os.getenv("MONITOREO_LTE_PATH", "/opt/eir/var/tps/tpscontrol")
    gsm_path = os.getenv("MONITOREO_GSM_PATH", "/opt/eir/var/tps/tpscontrol")

    mostrar_resumen_tps("LTE", lte_path, leer_lte, analizar_lte)
    mostrar_resumen_tps("GSM", gsm_path, leer_gsm, analizar_gsm)

    print("\n[SSH] Conexión remota")
    try:
        datos_ssh = conectar_ssh()
        if datos_ssh:
            print(f"- Servidor: {datos_ssh['usuario']}@{datos_ssh['host']}:{datos_ssh['puerto']}")
            if datos_ssh['salida']:
                print("- Respuesta remota:")
                print(datos_ssh['salida'])
            if datos_ssh['error']:
                print("- Errores SSH:")
                print(datos_ssh['error'])
        else:
            print("- No hay configuración SSH activa. Define MONITOREO_SSH_HOST y MONITOREO_SSH_USER.")
    except Exception as exc:
        print(f"- La conexión SSH no pudo iniciarse: {exc}")


if __name__ == "__main__":
    main()
