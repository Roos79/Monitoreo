import os
import json

def ejecutar_comando_remoto(cliente_ssh, comando):
    """Ejecuta un comando en el servidor remoto y devuelve la salida limpia."""
    stdin, stdout, stderr = cliente_ssh.exec_command(comando)
    salida = stdout.read().decode("utf-8", errors="ignore").strip()
    error = stderr.read().decode("utf-8", errors="ignore").strip()
    return salida, error

def conectar_y_recolectar():
    """Establece conexión SSH y ejecuta los recolectores en el servidor remoto."""
    host = os.getenv("10.33.112.22")
    usuario = os.getenv("eir4cad")
    puerto = int(os.getenv("22"))
    clave = os.getenv("Claro_eir2024*")

    if not host or not usuario:
        return {"error": "Falta configuración SSH"}

    try:
        import paramiko
    except ImportError as exc:
        raise RuntimeError("Falta la dependencia 'paramiko'. Instálala con pip.") from exc

    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs = {"hostname": host, "username": usuario, "port": puerto}
    if clave:
        kwargs["key_filename"] = clave

    try:
        cliente.connect(**kwargs)
        
        # 1. Ejecutar recolectores de hardware (Devuelven JSON en su salida estándar si los llamamos directamente)
        # Nota: Asumimos que los scripts recolectores están alojados en el servidor en /opt/eir/scripts/
        cmd_cpu = "python3 -c 'import cpu; print(json.dumps(cpu.capturar_particiones()))'"
        salida_cpu, err_cpu = ejecutar_comando_remoto(cliente, cmd_cpu)
        
        cmd_mem = "python3 -c 'import memoria; print(json.dumps(memoria.capturar_memoria()))'"
        salida_mem, err_mem = ejecutar_comando_remoto(cliente, cmd_mem)

        # 2. Ejecutar recolectores de transacciones LTE y GSM
        # Le pasamos las rutas de los logs del servidor por variables de entorno remotas si es necesario
        lte_path = os.getenv("MONITOREO_LTE_PATH", "/opt/eir/var/tps/tpscontrol")
        gsm_path = os.getenv("MONITOREO_GSM_PATH", "/opt/eir/var/stats/su1-tps-eir_stats")
        
        cmd_lte = f"python3 -c 'import lte; import json; print(json.dumps(lte.analizar_transacciones(lte.leer_transacciones(\"{lte_path}\"))))'"
        salida_lte, err_lte = ejecutar_comando_remoto(cliente, cmd_lte)
        
        cmd_gsm = f"python3 -c 'import gsm; import json; print(json.dumps(gsm.analizar_transacciones(gsm.leer_transacciones(\"{gsm_path}\"))))'"
        salida_gsm, err_gsm = ejecutar_comando_remoto(cliente, cmd_gsm)

        cliente.close()

        # Retornamos los datos estructurados listos para que main.py los pinte
        return {
            "estado": "OK",
            "host": host,
            "usuario": usuario,
            "cpu": json.loads(salida_cpu) if salida_cpu else None,
            "memoria": json.loads(salida_mem) if salida_mem else None,
            "lte": json.loads(salida_lte) if salida_lte else None,
            "gsm": json.loads(salida_gsm) if salida_gsm else None,
            "errores": {"cpu": err_cpu, "memoria": err_mem, "lte": err_lte, "gsm": err_gsm}
        }

    except Exception as e:
        return {"estado": "ERROR", "error": f"Fallo en la conexión remota: {str(e)}"}