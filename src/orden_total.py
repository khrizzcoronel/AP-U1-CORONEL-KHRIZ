import argparse
from pathlib import Path


def ordenar(carpeta):
    registros = []
    for nombre in ("coordinador", "puerta1", "puerta2", "puerta3"):
        registros.extend((carpeta / f"{nombre}.log").read_text(encoding="utf-8").splitlines())

    def clave(linea):
        reloj, proceso, _, _ = linea.split(";", 3)
        return int(reloj), int(proceso)

    registros.sort(key=clave)
    (carpeta / "orden_total.log").write_text("\n".join(registros) + "\n", encoding="utf-8")
    return len(registros)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--logs", type=Path, default=Path("logs"))
    args = parser.parse_args()
    print(f"{ordenar(args.logs)} eventos en {args.logs / 'orden_total.log'}")


if __name__ == "__main__":
    main()
