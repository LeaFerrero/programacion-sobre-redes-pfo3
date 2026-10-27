"""Servidor: recibe tareas de los clientes por socket y las distribuye
a los workers con balanceo round-robin (con reintento si un worker cae).

Uso: python servidor.py
"""
import itertools
import json
import socket
import threading

HOST = "127.0.0.1"
PUERTO = 5000
WORKERS = [("127.0.0.1", 6001), ("127.0.0.1", 6002), ("127.0.0.1", 6003)]

_rr = itertools.cycle(range(len(WORKERS)))
_lock = threading.Lock()


def siguiente_worker() -> int:
    with _lock:
        return next(_rr)


def enviar_a_worker(tarea: dict) -> dict:
    """Prueba cada worker empezando por el que toca en round-robin."""
    inicio = siguiente_worker()
    for i in range(len(WORKERS)):
        direccion = WORKERS[(inicio + i) % len(WORKERS)]
        try:
            with socket.create_connection(direccion, timeout=5) as w:
                w.sendall((json.dumps(tarea) + "\n").encode("utf-8"))
                linea = w.makefile("r", encoding="utf-8").readline()
                return json.loads(linea)
        except (OSError, json.JSONDecodeError):
            print(f"[servidor] worker {direccion} no disponible, probando otro")
    return {"ok": False, "error": "No hay workers disponibles"}


def atender_cliente(conn: socket.socket, addr):
    print(f"[servidor] cliente conectado: {addr}")
    with conn:
        for linea in conn.makefile("r", encoding="utf-8"):
            linea = linea.strip()
            if not linea:
                continue
            try:
                tarea = json.loads(linea)
                respuesta = enviar_a_worker(tarea)
                respuesta["id"] = tarea.get("id")
            except json.JSONDecodeError:
                respuesta = {"ok": False, "error": "JSON inválido"}
            conn.sendall((json.dumps(respuesta) + "\n").encode("utf-8"))
    print(f"[servidor] cliente desconectado: {addr}")


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PUERTO))
    srv.listen()
    print(f"[servidor] escuchando en {HOST}:{PUERTO}")
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=atender_cliente, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[servidor] cerrando...")
    finally:
        srv.close()


if __name__ == "__main__":
    main()
