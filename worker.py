"""Worker: recibe tareas por socket y las procesa con un pool de hilos.

Uso: python worker.py <puerto> [hilos]
"""
import json
import math
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

HOST = "127.0.0.1"


def procesar(tarea: dict):
    tipo = tarea.get("tipo")
    datos = tarea.get("datos")
    if tipo == "suma":
        return sum(datos)
    if tipo == "factorial":
        return math.factorial(int(datos))
    if tipo == "mayusculas":
        return str(datos).upper()
    if tipo == "fibonacci":
        a, b = 0, 1
        for _ in range(int(datos)):
            a, b = b, a + b
        return a
    raise ValueError(f"Tipo de tarea desconocido: {tipo}")


def atender(conn: socket.socket, nombre: str):
    with conn:
        try:
            linea = conn.makefile("r", encoding="utf-8").readline()
            if not linea:
                return
            tarea = json.loads(linea)
            try:
                resultado = {"ok": True, "resultado": procesar(tarea), "worker": nombre}
            except Exception as e:  # error de la tarea, no del worker
                resultado = {"ok": False, "error": str(e), "worker": nombre}
            conn.sendall((json.dumps(resultado) + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[{nombre}] error: {e}")


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
    hilos = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    nombre = f"worker-{puerto}"

    pool = ThreadPoolExecutor(max_workers=hilos)
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, puerto))
    srv.listen()
    print(f"[{nombre}] escuchando en {HOST}:{puerto} con {hilos} hilos")

    try:
        while True:
            conn, addr = srv.accept()
            pool.submit(atender, conn, nombre)
    except KeyboardInterrupt:
        print(f"\n[{nombre}] cerrando...")
    finally:
        pool.shutdown(wait=False)
        srv.close()


if __name__ == "__main__":
    main()
