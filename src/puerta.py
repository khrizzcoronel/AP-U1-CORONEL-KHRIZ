import sys

from .protocolo import Config, argumentos, solicitar

NOMBRES = {1: "Norte", 2: "Sur", 3: "Este"}
ORDENES = ("entrar", "salir", "estado")


def main():
    parser = argumentos()
    parser.add_argument("id", type=int, choices=NOMBRES)
    args = parser.parse_args()
    config = Config.leer(args.config)
    print(f"P{args.id} {NOMBRES[args.id]} | {' / '.join(ORDENES)}", flush=True)
    for linea in sys.stdin:
        orden = linea.strip().lower()
        if orden not in ORDENES:
            print("Orden desconocida", flush=True)
            continue
        try:
            respuesta = solicitar(config, args.id, orden.upper())
        except (OSError, ValueError):
            print(f"{orden.upper()}: operación no confirmada por el coordinador", flush=True)
        else:
            print(f"{orden.upper()}: {respuesta['resultado']} {respuesta['motivo']} "
                  f"{respuesta['dentro']}/{respuesta['aforo']}", flush=True)


if __name__ == "__main__":
    main()
