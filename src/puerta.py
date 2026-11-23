import sys
from threading import Event, Thread
from time import monotonic

from .bitacora import Bitacora

from .protocolo import Config, argumentos, solicitar

NOMBRES = {1: "Norte", 2: "Sur", 3: "Este"}
ORDENES = ("entrar", "salir", "estado")


def latidos(config, puerta, bitacora, detener):
    while not detener.is_set():
        inicio = monotonic()
        try:
            solicitar(config, puerta, "LATIDO", bitacora)
        except (OSError, ValueError) as error:
            bitacora.evento("ERROR_LATIDO", error)
        detener.wait(max(0, 2 - (monotonic() - inicio)))


def consola(config, puerta, bitacora):
    for linea in sys.stdin:
        orden = linea.strip().lower()
        bitacora.evento("ORDEN", orden)
        if orden not in ORDENES:
            print("Orden desconocida", flush=True)
            continue
        try:
            respuesta = solicitar(config, puerta, orden.upper(), bitacora)
        except (OSError, ValueError) as error:
            bitacora.evento("ERROR_ORDEN", error)
            print(f"{orden.upper()}: operación no confirmada por el coordinador", flush=True)
        else:
            estado = " ".join(f"P{puerta_id}={valor}"
                              for puerta_id, valor in respuesta["puertas"].items())
            print(f"{orden.upper()}: {respuesta['resultado']} {respuesta['motivo']} "
                  f"{respuesta['dentro']}/{respuesta['aforo']} | {estado}", flush=True)


def main():
    parser = argumentos()
    parser.add_argument("id", type=int, choices=NOMBRES)
    args = parser.parse_args()
    config = Config.leer(args.config)
    print(f"P{args.id} {NOMBRES[args.id]} | {' / '.join(ORDENES)}", flush=True)
    bitacora = Bitacora(args.logs, args.id)
    bitacora.evento("INICIO", NOMBRES[args.id])
    detener = Event()
    hilo = Thread(target=latidos, args=(config, args.id, bitacora, detener))
    hilo.start()
    try:
        consola(config, args.id, bitacora)
    except KeyboardInterrupt:
        pass
    finally:
        detener.set()
        hilo.join()



if __name__ == "__main__":
    main()
