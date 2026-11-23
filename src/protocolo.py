import argparse
import json
import socket
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class Config:
    host: str
    puerto: int
    aforo: int
    token: str

    @property
    def direccion(self):
        return self.host, self.puerto

    @classmethod
    def leer(cls, ruta):
        valores = dict(
            linea.strip().split("=", 1)
            for linea in Path(ruta).read_text(encoding="utf-8").splitlines()
            if linea.strip() and not linea.lstrip().startswith("#")
        )
        return cls(valores["host"], int(valores["puerto"]),
                   int(valores["aforo"]), valores["token"])


def argumentos():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.properties")
    parser.add_argument("--logs", type=Path, default=Path("logs"))
    return parser


def escribir(mensaje):
    return (json.dumps(mensaje, ensure_ascii=False) + "\n").encode("utf-8")


def leer(archivo):
    linea = archivo.readline(8193)
    if not linea:
        return None
    if len(linea) > 8192 or not linea.endswith(b"\n"):
        raise ValueError("Mensaje incompleto o demasiado largo")
    valor = json.loads(linea)
    if not isinstance(valor, dict):
        raise ValueError("Se esperaba un objeto JSON")
    return valor


def solicitar(config, puerta, tipo, *, token=None):
    mensaje = dict(tipo=tipo, token=config.token if token is None else token,
                   puerta=puerta, lamport=0, solicitud=uuid4().hex)
    with socket.create_connection(config.direccion, timeout=1.5) as conexion:
        conexion.sendall(escribir(mensaje))
        with conexion.makefile("rb") as entrada:
            respuesta = leer(entrada)
    if respuesta is None or respuesta.get("solicitud") != mensaje["solicitud"]:
        raise ValueError("Respuesta ausente o no correlacionada")
    return respuesta
