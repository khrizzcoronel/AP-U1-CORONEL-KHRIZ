# AforoSeguro de práctica

Prueba practica. primer evaluacion sumativa.

## Codigos de sesion

Codigo de sesion 1: `KD55-TB` y sesion 2: `662D-M6`

## Requisitos y arranque

Python 3.11 o superior y su biblioteca estándar. Ejecuta desde la raíz
del repositorio. Usando `py`.

```sh
py -m compileall -q src pruebas
py -m src.coordinador
```

Una vez que el coordinador anuncie su dirección, abre una terminal por puerta:

```sh
py -m src.puerta 1
py -m src.puerta 2
py -m src.puerta 3
```

Escribe `entrar`, `salir` o `estado` y pulsa Intro. Detén cada proceso con
Ctrl+C. `config.properties` fija la dirección central, el token
y el aforo. Los clientes usan puertos locales. Puedes pasar
`--config RUTA --logs CARPETA` a los cuatro procesos de red y de carga. Usa
una carpeta distinta de `logs/` para conservar la evidencia incluida y una
sola instancia por ID en cada carpeta.

## Protocolo TCP

Cada mensaje es un objeto JSON UTF-8 terminado en salto de línea. Una conexión puede transportar varias solicitudes consecutivas. Cada respuesta repite el identificador de correlación.

```json
{"tipo":"ENTRAR","token":"demostracion-local","puerta":2,"lamport":17,"solicitud":"ejemplo-1"}
{"tipo":"RESPUESTA","resultado":"PERMITIDA","motivo":"","dentro":8,"aforo":10,"puertas":{"1":"ACTIVA","2":"ACTIVA","3":"CAIDA"},"lamport":19,"solicitud":"ejemplo-1"}
```

## Carga, orden total y pruebas

Inicia un coordinador vacío y ejecuta el generador en otra terminal. Repite
después de reiniciar el coordinador con `--inseguro`. El generador sustituye a
las puertas durante la prueba de carga y escribe bitácoras para sus tres IDs.

```sh
py -m src.coordinador --logs corrida-normal
py -m src.prueba_carga --logs corrida-normal
py -m src.orden_total --logs corrida-normal
```

Usa `corrida-insegura` como carpeta para la segunda ejecución. Ejecuta
`orden_total` una vez terminados los procesos que escriben en esa carpeta.
Cada línea de las bitácoras contiene
`lamport;id_proceso;evento;detalle`. La ocupación se reinicia con el coordinador,
pero cada proceso recupera su última marca de Lamport de su bitácora.

## Código reutilizado

No se reutilizó código de repositorios propios anteriores. El código de este
repositorio fue generado con asistencia de IA para el ejercicio de práctica.
