import hmac
import socketserver
from threading import Lock

from .protocolo import Config, argumentos, escribir, leer


class Coordinador(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, config):
        self.config = config
        self.dentro = 0
        self.bloqueo = Lock()
        super().__init__(config.direccion, Conexion)

    def operar(self, tipo):
        with self.bloqueo:
            motivo = self.impedimento(tipo)
            if not motivo:
                self.actualizar(tipo)
            return motivo, self.dentro

    def impedimento(self, tipo):
        if tipo == "ENTRAR" and self.dentro >= self.config.aforo:
            return "aforo completo"
        if tipo == "SALIR" and self.dentro <= 0:
            return "nadie dentro"
        return ""

    def actualizar(self, tipo):
        self.dentro += {"ENTRAR": 1, "SALIR": -1, "ESTADO": 0}[tipo]

    def responder(self, solicitud):
        token = solicitud.get("token")
        tipo = solicitud.get("tipo")
        puerta = solicitud.get("puerta")
        dentro = self.dentro
        if not isinstance(token, str) or not hmac.compare_digest(
            token.encode("utf-8"), self.config.token.encode("utf-8")
        ):
            motivo = "token inválido"
        elif type(puerta) is not int or puerta not in (1, 2, 3):
            motivo = "puerta inválida"
        elif tipo not in ("ENTRAR", "SALIR", "ESTADO"):
            motivo = "orden inválida"
        else:
            motivo, dentro = self.operar(tipo)
        return dict(tipo="RESPUESTA", resultado="RECHAZADA" if motivo else "PERMITIDA",
                    motivo=motivo, dentro=dentro, aforo=self.config.aforo,
                    lamport=0, solicitud=solicitud.get("solicitud"))


class Conexion(socketserver.StreamRequestHandler):
    timeout = 2

    def handle(self):
        try:
            while (solicitud := leer(self.rfile)) is not None:
                self.wfile.write(escribir(self.server.responder(solicitud)))
        except (OSError, ValueError):
            return


def main():
    args = argumentos().parse_args()
    config = Config.leer(args.config)
    with Coordinador(config) as servidor:
        print(f"Coordinador en {servidor.server_address}", flush=True)
        servidor.serve_forever()


if __name__ == "__main__":
    main()
