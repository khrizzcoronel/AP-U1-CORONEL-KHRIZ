import hmac
import socketserver
from threading import Event, Lock, Thread
from time import monotonic, sleep

from .bitacora import Bitacora
from .protocolo import Config, argumentos, escribir, leer, marca


class Coordinador(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, config, inseguro, bitacora):
        self.inseguro = inseguro
        self.bitacora = bitacora
        self.latidos = {puerta: None for puerta in (1, 2, 3)}
        self.config = config
        self.dentro = 0
        self.bloqueo = Lock()
        super().__init__(config.direccion, Conexion)

    def vigilar(self, detener):
        while not detener.wait(0.05):
            with self.bloqueo:
                ahora = monotonic()
                for puerta, ultimo in self.latidos.items():
                    if ultimo is not None and ahora - ultimo >= 6:
                        self.latidos[puerta] = None
                        self.bitacora.evento("CAIDA", f"P{puerta}")

    def latido(self, puerta):
        with self.bloqueo:
            if self.latidos[puerta] is None:
                self.bitacora.evento("ACTIVA", f"P{puerta}")
            self.latidos[puerta] = monotonic()
            return "", self.dentro

    def operar(self, tipo):
        if self.inseguro and tipo == "ENTRAR":
            with self.bloqueo:
                motivo = self.impedimento(tipo)
            if not motivo:
                sleep(0.05)
                with self.bloqueo:
                    self.actualizar(tipo)
            return motivo, self.dentro

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
        identificador = solicitud.get("solicitud")
        if not isinstance(identificador, str) or len(identificador) > 64:
            raise ValueError("Identificador de solicitud inválido")
        self.bitacora.evento("RECEPCION", f"{tipo} {identificador}", marca(solicitud))
        with self.bloqueo:
            dentro = self.dentro
        if not isinstance(token, str) or not hmac.compare_digest(
            token.encode("utf-8"), self.config.token.encode("utf-8")
        ):
            motivo = "token inválido"
        elif type(puerta) is not int or puerta not in (1, 2, 3):
            motivo = "puerta inválida"
        elif tipo == "LATIDO":
            motivo, dentro = self.latido(puerta)
        elif tipo not in ("ENTRAR", "SALIR", "ESTADO"):
            motivo = "orden inválida"
        else:
            motivo, dentro = self.operar(tipo)
        with self.bloqueo:
            puertas = {puerta: "ACTIVA" if ultimo is not None else "CAIDA"
                       for puerta, ultimo in self.latidos.items()}
        if motivo:
            self.bitacora.evento("RECHAZO", f"{identificador} {motivo}")
        reloj = self.bitacora.evento("ENVIO", f"RESPUESTA {identificador}")
        return dict(tipo="RESPUESTA", resultado="RECHAZADA" if motivo else "PERMITIDA",
                    motivo=motivo, dentro=dentro, aforo=self.config.aforo,
                    puertas=puertas, lamport=reloj, solicitud=identificador)


class Conexion(socketserver.StreamRequestHandler):
    timeout = 2

    def handle(self):
        try:
            while (solicitud := leer(self.rfile)) is not None:
                self.wfile.write(escribir(self.server.responder(solicitud)))
        except (OSError, ValueError) as error:
            self.server.bitacora.evento("ERROR", error)


def main():
    parser = argumentos()
    parser.add_argument("--inseguro", action="store_true")
    args = parser.parse_args()
    config = Config.leer(args.config)
    bitacora = Bitacora(args.logs, 0)
    with Coordinador(config, args.inseguro, bitacora) as servidor:
        bitacora.evento("INICIO", "inseguro" if args.inseguro else "normal")
        detener = Event()
        vigilante = Thread(target=servidor.vigilar, args=(detener,))
        vigilante.start()
        try:
            print(f"Coordinador en {servidor.server_address}", flush=True)
            servidor.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            detener.set()
            vigilante.join()


if __name__ == "__main__":
    main()
