# AforoSeguro de práctica

Prototipo didáctico de control de aforo distribuido, desarrollado con asistencia
de IA. Las evidencias corresponden a una práctica en Linux.

## Requisitos y arranque

Usa Python 3.11 o superior y su biblioteca estándar. Ejecuta desde la raíz
del repositorio. En Windows puedes sustituir `python3` por `py -3`.

```sh
python3 -m compileall -q src pruebas
python3 -m src.coordinador
```

Una vez que el coordinador anuncie su dirección, abre una terminal por puerta:

```sh
python3 -m src.puerta 1
python3 -m src.puerta 2
python3 -m src.puerta 3
```

Escribe `entrar`, `salir` o `estado` y pulsa Intro. Detén cada proceso con
Ctrl+C. `config.properties` fija la dirección central, el token de demostración
y el aforo. Los clientes usan puertos locales efímeros. Puedes pasar
`--config RUTA --logs CARPETA` a los cuatro procesos de red y de carga. Usa
una carpeta distinta de `logs/` para conservar la evidencia incluida y una
sola instancia por ID en cada carpeta.

## Protocolo TCP

Cada mensaje es un objeto JSON UTF-8 terminado en salto de línea, con un máximo
de 8192 bytes incluido el delimitador. Una conexión puede transportar varias
solicitudes consecutivas. Cada respuesta repite el identificador de correlación.

```json
{"tipo":"ENTRAR","token":"demostracion-local","puerta":2,"lamport":17,"solicitud":"ejemplo-1"}
{"tipo":"RESPUESTA","resultado":"PERMITIDA","motivo":"","dentro":8,"aforo":10,"puertas":{"1":"ACTIVA","2":"ACTIVA","3":"CAIDA"},"lamport":19,"solicitud":"ejemplo-1"}
```

Los otros tipos de solicitud son `SALIR`, `ESTADO` y `LATIDO`. Solo un latido
autenticado actualiza el estado de actividad. El token se envía en texto plano,
adecuado para esta demostración restringida a loopback. Ante una respuesta
perdida, la puerta muestra que la operación no se confirmó. Un cambio ya
procesado podría quedar aplicado, por lo que la puerta evita reintentos
automáticos.

## Carga, orden total y pruebas

Inicia un coordinador vacío y ejecuta el generador en otra terminal. Repite
después de reiniciar el coordinador con `--inseguro`. El generador sustituye a
las puertas durante la prueba de carga y escribe bitácoras para sus tres IDs.

```sh
python3 -m src.coordinador --logs corrida-normal
python3 -m src.prueba_carga --logs corrida-normal
python3 -m src.orden_total --logs corrida-normal
```

Usa `corrida-insegura` como carpeta para la segunda ejecución. Ejecuta
`orden_total` una vez terminados los procesos que escriben en esa carpeta.
Cada línea de las bitácoras contiene
`lamport;id_proceso;evento;detalle`. La ocupación se reinicia con el coordinador,
pero cada proceso recupera su última marca de Lamport de su bitácora.

```sh
python3 -m pruebas.integracion
```

La prueba integrada ejecuta E0–E6 con un puerto local y registros temporales.
Para guardar una nueva corrida en otra carpeta, usa
`python3 -m pruebas.integracion --evidencia RUTA`. Las imágenes incluidas son
renderizaciones de las transcripciones de esa ejecución. E0 verifica una conexión
loopback en Linux. El escenario de desconexión física pertenece a la sesión
supervisada de la guía.

## Compilar los PDF

Desde la raíz del proyecto, entra a `docs` y ejecuta:

```sh
cd docs
pdflatex -halt-on-error informe.tex
pdflatex -halt-on-error informe.tex
pdflatex -halt-on-error entrega_SGA.tex
```

El informe usa `graphicx`, `fontenc` y `geometry` de TeX Live.

## Código reutilizado

No se reutilizó código de repositorios propios anteriores. El código de este
repositorio fue generado con asistencia de IA para el ejercicio de práctica.
