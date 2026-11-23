import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from .protocolo import Config, argumentos, solicitar


def ejecutar(config):
    puertas = [puerta for puerta in (1, 2, 3) for _ in range(10)]
    barrera = Barrier(len(puertas))

    def entrar(puerta):
        barrera.wait(timeout=5)
        try:
            return solicitar(config, puerta, "ENTRAR")["resultado"]
        except (OSError, ValueError):
            return "ERROR"

    with ThreadPoolExecutor(max_workers=len(puertas)) as ejecutor:
        resultados = list(ejecutor.map(entrar, puertas))
    return dict(permitidas=resultados.count("PERMITIDA"),
                rechazadas=resultados.count("RECHAZADA"),
                errores=resultados.count("ERROR"),
                dentro=solicitar(config, 1, "ESTADO")["dentro"])


def main():
    args = argumentos().parse_args()
    print(json.dumps(ejecutar(Config.leer(args.config))))


if __name__ == "__main__":
    main()
