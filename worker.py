"""Worker: recibe tareas por socket y las procesa con un pool de hilos.

Uso: python worker.py <puerto> [hilos]
El puerto debe ser uno de los que conoce el servidor (6001, 6002 o 6003).
"""

import json
import math
import socket
import sqlite3
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HOST = "127.0.0.1"
PUERTOS_WORKERS = (6001, 6002, 6003)  # deben coincidir con WORKERS en servidor.py
DB_NAME = "tareas.db"  # SQLite emula a PostgreSQL; la comparten todos los workers


def inicializar_db():
    """Crea la tabla de tareas si no existe."""
    conexion = sqlite3.connect(DB_NAME, timeout=10)
    try:
        conexion.execute("""
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarea_id INTEGER,
                tipo TEXT,
                datos TEXT,
                ok INTEGER NOT NULL,
                resultado TEXT,
                worker TEXT NOT NULL,
                fecha TEXT NOT NULL
            )
        """)
        conexion.commit()
    finally:
        conexion.close()


def guardar_tarea(tarea: dict, respuesta: dict):
    """Guarda la tarea y su resultado (o error). Cada llamada usa su propia
    conexión, así es segura entre hilos y entre procesos."""
    conexion = None
    try:
        conexion = sqlite3.connect(DB_NAME, timeout=10)
        conexion.execute(
            "INSERT INTO tareas (tarea_id, tipo, datos, ok, resultado, worker, fecha) " "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                tarea.get("id"),
                tarea.get("tipo"),
                json.dumps(tarea.get("datos")),
                1 if respuesta["ok"] else 0,
                str(respuesta.get("resultado", respuesta.get("error"))),
                respuesta["worker"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conexion.commit()
    except sqlite3.Error as e:
        print(f"[{respuesta['worker']}] error al guardar en la base: {e}")
    finally:
        if conexion:
            conexion.close()


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
            guardar_tarea(tarea, resultado)
        except Exception as e:
            print(f"[{nombre}] error: {e}")


def main():
    try:
        puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 6001
        hilos = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    except ValueError:
        print("Uso: python worker.py <puerto> [hilos] (ambos números enteros)")
        return
    if puerto not in PUERTOS_WORKERS:
        print("Puerto inválido. Los workers deben usar uno de estos: " f"{', '.join(map(str, PUERTOS_WORKERS))}.")
        return
    if hilos < 1:
        print("La cantidad de hilos debe ser al menos 1.")
        return

    try:
        inicializar_db()
    except sqlite3.Error as e:
        print(f"No se pudo inicializar la base de datos: {e}")
        return

    nombre = f"worker-{puerto}"

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind((HOST, puerto))
        srv.listen()
    except OSError as e:
        print(f"No se pudo usar el puerto {puerto}: {e}")
        srv.close()
        return

    pool = ThreadPoolExecutor(max_workers=hilos)
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
