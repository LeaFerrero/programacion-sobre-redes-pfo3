"""Cliente: envía tareas al servidor por socket y muestra los resultados.

Uso: python cliente.py
"""
import json
import socket

HOST = "127.0.0.1"
PUERTO = 5000

TAREAS = [
    {"id": 1, "tipo": "suma", "datos": [1, 2, 3, 4, 5]},
    {"id": 2, "tipo": "factorial", "datos": 10},
    {"id": 3, "tipo": "mayusculas", "datos": "hola sistemas distribuidos"},
    {"id": 4, "tipo": "fibonacci", "datos": 30},
    {"id": 5, "tipo": "inexistente", "datos": None},  # prueba de error
]


def main():
    with socket.create_connection((HOST, PUERTO), timeout=10) as s:
        lector = s.makefile("r", encoding="utf-8")
        for tarea in TAREAS:
            s.sendall((json.dumps(tarea) + "\n").encode("utf-8"))
            respuesta = json.loads(lector.readline())
            if respuesta.get("ok"):
                print(f"Tarea {respuesta['id']} -> {respuesta['resultado']} "
                      f"(procesada por {respuesta['worker']})")
            else:
                print(f"Tarea {respuesta.get('id')} -> ERROR: {respuesta['error']}")


if __name__ == "__main__":
    main()
