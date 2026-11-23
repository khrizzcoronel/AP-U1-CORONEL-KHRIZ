from threading import Lock


class Bitacora:
    def __init__(self, carpeta, proceso):
        carpeta.mkdir(parents=True, exist_ok=True)
        self.ruta = carpeta / ("coordinador.log" if proceso == 0 else f"puerta{proceso}.log")
        self.proceso = proceso
        self.bloqueo = Lock()
        self.reloj = 0
        if self.ruta.exists():
            with self.ruta.open(encoding="utf-8") as archivo:
                self.reloj = max((int(linea.split(";", 1)[0]) for linea in archivo), default=0)

    def evento(self, evento, detalle, recibido=0):
        detalle = str(detalle).replace("\n", "\\n").replace("\r", "\\r")
        with self.bloqueo:
            self.reloj = max(self.reloj, recibido) + 1
            with self.ruta.open("a", encoding="utf-8") as archivo:
                archivo.write(f"{self.reloj};{self.proceso};{evento};{detalle}\n")
            return self.reloj
