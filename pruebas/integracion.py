"""Ejecuta E0–E6 en procesos independientes y verifica sus resultados."""
import argparse
import getpass
import json
import platform
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from datetime import datetime
from pathlib import Path
from queue import Queue
from threading import Thread
from time import monotonic, sleep
from uuid import uuid4

from src.bitacora import Bitacora
from src.protocolo import escribir, leer


@contextmanager
def proceso(modulo, *args):
    comando = [sys.executable, "-m", f"src.{modulo}", *map(str, args)]
    with subprocess.Popen(comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, text=True, encoding="utf-8") as instancia:
        salida = Queue()

        def leer_salida():
            for linea in instancia.stdout:
                salida.put(linea.strip())
            salida.put(None)

        lector = Thread(target=leer_salida)
        lector.start()
        try:
            yield instancia, salida
        finally:
            detener(instancia)
            lector.join()


def detener(instancia):
    if instancia.poll() is None:
        instancia.terminate()
        try:
            instancia.wait(timeout=3)
        except subprocess.TimeoutExpired:
            instancia.kill()
            instancia.wait()


def linea(salida):
    texto = salida.get(timeout=5)
    if texto is None:
        raise RuntimeError("El proceso terminó antes de responder")
    return texto


def ordenar_consola(proceso_puerta, orden):
    instancia, salida = proceso_puerta
    instancia.stdin.write(orden + "\n")
    instancia.stdin.flush()
    return linea(salida)


def esperar(predicado, segundos):
    limite = monotonic() + segundos
    while monotonic() < limite:
        valor = predicado()
        if valor:
            return valor
        sleep(0.05)
    raise AssertionError("Se agotó el plazo de espera")


class Escenarios(unittest.TestCase):
    evidencia = None

    def registrar(self, numero, *salidas):
        if self.evidencia is None:
            return
        imagenes = self.evidencia / "docs" / "img"
        imagenes.mkdir(parents=True, exist_ok=True)
        encabezado = (f"AforoSeguro de práctica | {numero}\n"
                      f"Usuario: {getpass.getuser()} | Equipo: {socket.gethostname()}\n"
                      f"Fecha: {datetime.now().astimezone().isoformat(timespec='seconds')}\n"
                      f"Sistema: {platform.system()}\n\n")
        (imagenes / f"{numero}.txt").write_text(encabezado + "\n".join(salidas) + "\n",
                                               encoding="utf-8")

    def test_escenarios(self):
        with tempfile.TemporaryDirectory() as temporal:
            self.escenarios(Path(temporal))

    def escenarios(self, temporal):
        logs = temporal / "logs"
        config = temporal / "config.properties"
        with socket.socket() as reserva:
            reserva.bind(("127.0.0.1", 0))
            direccion = reserva.getsockname()
        config.write_text(f"host={direccion[0]}\npuerto={direccion[1]}\n"
                          "aforo=10\ntoken=demostracion-local\n", encoding="utf-8")
        opciones = ("--config", config, "--logs", logs)

        with ExitStack() as procesos:
            coordinador, salida = procesos.enter_context(proceso("coordinador", *opciones))
            inicio = linea(salida)
            puertas = {
                puerta: procesos.enter_context(proceso("puerta", puerta, *opciones))
                for puerta in (1, 2, 3)
            }
            for instancia, salida in puertas.values():
                self.assertRegex(linea(salida), r"^P[123] ")
            p1, p2, p3 = puertas.values()
            estado = esperar(lambda: (texto if "P3=ACTIVA" in
                             (texto := ordenar_consola(p1, "estado")) and
                             "P1=ACTIVA" in texto and "P2=ACTIVA" in texto else None), 3)
            self.registrar("E0", inicio, estado, "Conexión local por 127.0.0.1 comprobada.")

            vacio = ordenar_consola(p2, "salir")
            self.assertIn("nadie dentro", vacio)
            entradas = [ordenar_consola(p, "entrar") for p in puertas.values()]
            self.assertTrue(all("PERMITIDA" in texto for texto in entradas))
            salida_p2 = ordenar_consola(p2, "salir")
            self.assertIn("PERMITIDA", salida_p2)
            estados = [ordenar_consola(p, "estado") for p in puertas.values()]
            self.assertTrue(all("2/10" in texto for texto in estados))
            self.registrar("E1", vacio, *entradas, salida_p2,
                           *(f"P{i} {texto}" for i, texto in enumerate(estados, 1)))

            for _ in range(2):
                self.assertIn("PERMITIDA", ordenar_consola(p1, "salir"))
            for _ in range(10):
                self.assertIn("PERMITIDA", ordenar_consola(p1, "entrar"))
            llena = ordenar_consola(p1, "entrar")
            self.assertIn("RECHAZADA aforo completo 10/10", llena)
            bitacora = Bitacora(logs, 1)  # Solo se lee el reloj aquí.
            mensajes = [dict(tipo="ENTRAR", puerta=1, lamport=bitacora.reloj,
                             solicitud=uuid4().hex) for _ in range(2)]
            mensajes[0]["token"] = "incorrecto"
            datos = b"".join(map(escribir, mensajes))
            with socket.create_connection(direccion, timeout=2) as conexion:
                conexion.sendall(datos[:5])
                conexion.sendall(datos[5:])
                with conexion.makefile("rb") as entrada:
                    respuestas = [leer(entrada), leer(entrada)]
            for solicitud, respuesta in zip(mensajes, respuestas, strict=True):
                self.assertEqual(respuesta["solicitud"], solicitud["solicitud"])
                self.assertEqual(respuesta["motivo"], "token inválido")
                self.assertEqual(respuesta["resultado"], "RECHAZADA")
            registro = (logs / "coordinador.log").read_text(encoding="utf-8")
            for solicitud in mensajes:
                self.assertIn(f"{solicitud['solicitud']} token inválido", registro)
            self.registrar("E2", llena, "Token incorrecto: RECHAZADA (token inválido)",
                           "Token ausente: RECHAZADA (token inválido)",
                           "Ambos rechazos constan en coordinador.log.")

            antes = ordenar_consola(p1, "estado")
            detener(p3[0])
            inicio_espera = monotonic()

            def estado_p3(esperado):
                texto = ordenar_consola(p1, "estado")
                return texto if f"P3={esperado}" in texto else None

            self.assertIn("P3=ACTIVA", antes)
            caida = esperar(lambda: estado_p3("CAIDA"), 7)
            espera = monotonic() - inicio_espera
            reinicio = procesos.enter_context(proceso("puerta", 3, *opciones))
            linea(reinicio[1])
            recuperada = esperar(lambda: estado_p3("ACTIVA"), 3)
            eventos = (logs / "coordinador.log").read_text(encoding="utf-8").splitlines()
            transiciones = [evento for evento in eventos if evento.endswith((";ACTIVA;P3", ";CAIDA;P3"))]
            self.assertEqual([evento.split(";")[2] for evento in transiciones],
                             ["ACTIVA", "CAIDA", "ACTIVA"])
            self.registrar("E4", antes, f"P3 detenida. Detección tras {espera:.2f} s desde la parada.",
                           caida, recuperada, *transiciones)

            detener(coordinador)
            sin_coordinador = ordenar_consola(p1, "entrar")
            self.assertIn("operación no confirmada", sin_coordinador)
            self.registrar("E5", "Coordinador detenido con las tres puertas activas.",
                           f"P1 {sin_coordinador}")

        resultados = []
        for modo in ((), ("--inseguro",)):
            with proceso("coordinador", *opciones, *modo) as (_, salida):
                linea(salida)
                datos = subprocess.check_output([sys.executable, "-m", "src.prueba_carga", *map(str, opciones)],
                                                text=True, timeout=10)
                resultado = json.loads(datos)
                self.assertEqual(resultado["errores"], 0)
                self.assertEqual(resultado["permitidas"] + resultado["rechazadas"], 30)
                self.assertEqual(resultado["dentro"], resultado["permitidas"])
                resultados.append(resultado)
        self.assertEqual(resultados[0], dict(permitidas=10, rechazadas=20, errores=0, dentro=10))
        self.registrar("E3", f"Normal:   {json.dumps(resultados[0])}",
                       f"Inseguro: {json.dumps(resultados[1])}")

        salida = subprocess.check_output([sys.executable, "-m", "src.orden_total", "--logs", str(logs)],
                                         text=True, timeout=5).strip()
        registros = (logs / "orden_total.log").read_text(encoding="utf-8").splitlines()
        eventos = [(int(reloj), int(proceso_id), evento, detalle)
                   for reloj, proceso_id, evento, detalle in
                   (registro.split(";", 3) for registro in registros)]
        marcas = [(reloj, proceso_id) for reloj, proceso_id, _, _ in eventos]
        self.assertEqual(marcas, sorted(set(marcas)))
        envios = {detalle: reloj for reloj, _, evento, detalle in eventos if evento == "ENVIO"}
        pares = []
        for reloj, proceso_id, evento, detalle in eventos:
            if evento == "RECEPCION" and detalle in envios:
                self.assertLess(envios[detalle], reloj)
                if detalle.startswith("ENTRAR ") and len(pares) < 2:
                    pares.append(f"{detalle}: envío {envios[detalle]} < recepción {reloj} (P{proceso_id})")
        self.assertEqual(len(pares), 2)
        self.registrar("E6", salida.replace(str(logs), "logs"), *pares)
        if self.evidencia is not None:
            destino = self.evidencia / "logs"
            destino.mkdir(exist_ok=True)
            for archivo in logs.glob("*.log"):
                (destino / archivo.name).write_bytes(archivo.read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidencia", type=Path)
    argumentos = parser.parse_args()
    Escenarios.evidencia = argumentos.evidencia
    unittest.main(argv=[sys.argv[0]], verbosity=2)
