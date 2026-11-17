# Auditoría de UI — GenSubtitles

Hecha con la skill `frontend-design` instalada en `.cursor/skills/frontend-design/SKILL.md`, sobre la GUI de escritorio en `main` (`dc5796a`). No cambia código de la interfaz.

La skill está escrita para web. Aquí se aplica su criterio (identidad ligada al producto, tipografía, jerarquía, copy, y rechazo del look genérico) a CustomTkinter: fuentes instaladas, tokens de color y los widgets que ya existen. No se propone convertir la app en una página.

## Producto

GenSubtitles convierte el audio de un vídeo en un archivo de subtítulos, en local, sin mandar el audio a un servicio. Quien lo usa ya tiene un vídeo y quiere un `.srt` o un `.ssa`. El trabajo de la ventana es: elegir el vídeo, decir en qué idioma está y en cuál debe quedar, esperar mientras se transcribe, y recoger el archivo.

El material propio del producto es una línea de diálogo con dos tiempos. Eso, y no un panel de ajustes, es lo que la ventana debería hacer reconocible.

## Lo que se ve hoy

La ventana (`GenSubtitlesApp` en `gensubtitles/gui/main.py`) abre a un mínimo de 900×560, sin tamaño inicial, título "GenSubtitles", y una `CTkTabview` con seis pestañas al mismo nivel:

1. Generate Subtitles
2. Translate Subtitles
3. Extract Audio
4. Transcribe
5. Translate
6. Write Subtitle

Generate Subtitles parte la pestaña en dos tarjetas de `corner_radius=12` y color `surface`. A la izquierda: vídeo, archivo de salida, Generar y Limpiar campos, un estado, el log y (ocultos hasta que corre) el reloj, la barra y Cancelar. A la derecha, un título "Configuration" y los menús de idioma y formato.

Las cuatro pestañas de paso repiten la misma tarjeta: etiqueta, campo, botón de 80 px, otro campo, un botón de acción. Traducir subtítulos es un formulario parecido, suelto, sin esa tarjeta.

El tema por defecto es Material: fondo `#121212`, superficie `#1E1E1E`, acento `#2196F3`, hecho `#4CAF50`. Hay otras cinco paletas en `gensubtitles/gui/theme.py`. La escala tipográfica usa la fuente del sistema a 20 / 16 / 14 px, y en modo oscuro quita la negrita de los roles que deberían jerarquizar. El log usa Courier a 12 px.

Las constantes `SPACING_*` de `gensubtitles/gui/styles.py` no se usan en `main.py`. Los huecos están escritos a mano (4, 8, 12, 16).

## Hallazgos, por impacto

### 1. Seis destinos para dos tareas

Generar y traducir un subtítulo que ya existe son dos trabajos. Extraer, transcribir, traducir y escribir son un solo proceso, en orden. La barra los presenta como seis sitios iguales, y "Translate" queda al lado de "Translate Subtitles".

En una ventana de 900 px, seis etiquetas largas no caben como navegación. El usuario tiene que saber que el paso 4 es "Transcribe" y que el log habla de "Tab 4".

Hay un borrador de secuencia (etiquetas "1. Extract" … "4. Write SRT" y un interruptor de modo paso a paso) dentro del primer `def _log_to` de `main.py`, alrededor de las líneas 409–555. Esa definición la pisa el segundo `_log_to` (línea 557), así que el stepper no se construye nunca. La numeración sí correspondería aquí, porque el contenido es una secuencia. No corresponde como seis pestañas.

Cambio: dejar dos pestañas, Generar y Traducir un archivo. Dentro de Generar, una fila de cuatro etapas numeradas, visible solo cuando el modo paso a paso está activo. El botón de cada etapa dice el verbo de esa etapa ("Extraer audio"), y el estado de esa etapa usa la misma palabra ("Audio extraído"). Quitar del log "Pre-filled Tab 4 input" y decir qué archivo quedó listo.

### 2. El acento no es del producto, y en varias paletas el botón no se lee

`apply_accent_btn_style` pinta el botón con `accent` y no fija el color del texto. En Dark y Light el azul Material aguanta texto claro. En otras paletas el relleno es claro:

- Ocean Dark, acento `#64FFDA`
- Emerald, acento `#2ECC71`
- Monochrome, acento `#FFFFFF`
- Sunset se acerca a un fondo crema `#FFF8F0` con naranja `#E85D04`

Ocean y Emerald son el patrón de fondo casi negro con un verde ácido. Sunset es el patrón de crema con acento cálido. Monochrome usa el blanco como botón y como texto a la vez. Ninguna de esas elecciones sale de un subtítulo: salen del catálogo de temas oscuros.

El token de la superficie se llama, en la propia UI, "Surface / Card". Las tarjetas de Generar y las de los cuatro pasos comparten el mismo radio 12 y el mismo relleno, sin que el radio distinga algo.

Cambio: una sola paleta de trabajo, abajo, y tratar Ocean, Emerald y Sunset como looks de catálogo, no como la identidad. El color del texto del botón primario tiene que declararse junto al relleno, y comprobarse en cada paleta que se conserve. Un solo radio, solo en el control que es un botón; las zonas de formulario no necesitan tarjeta.

### 3. En oscuro, que es el tema de arranque, no hay jerarquía tipográfica

`font()` baja a peso normal los roles `header`, `subheader` y `body_bold` cuando el modo es Dark, para que la letra clara no se vea más gruesa. El efecto es el contrario: el título de 20 px y el cuerpo de 14 px quedan en el mismo peso, y 16 px de diferencia no alcanza para ordenar la pantalla. "Configuration" y "Color Palette" no se leen como títulos.

No hay una segunda familia. Courier aparece en el log, que sí es una consola, y también en los códigos hex de la paleta, donde la skill lo marca como adorno de plantilla.

Cambio: no quitar la negrita en oscuro; bajar un punto el cuerpo si la letra se ve pesada. Escala propuesta, en px: reloj 28, título de sección 18, cuerpo 14, ayuda 13. Una sola familia para los controles. La segunda familia es la fuente del subtítulo que el usuario ya elige en Ajustes, y solo se usa en la franja de subtítulo. Los hex de la paleta van en la misma familia del cuerpo.

### 4. El texto nombra el sistema, y a veces nombra dos acciones

La skill pide que cada control diga una sola cosa, con el verbo de lo que va a pasar, y que el aviso use las mismas palabras.

- "Translate / Convert" hace dos trabajos. El checkbox "Convert only (no translation — change format only)" repite la explicación.
- "No target" describe la ausencia de un campo. Quien usa la app quiere "Dejar el idioma original".
- "Input video *:" apila un asterisco y dos puntos. El asterisco no se explica en el formulario.
- "Default output dir:" y "Config file:" están abreviados. "Clear console on Clear fields:" habla de la consola del programa.
- "Cancel" está escrito en inglés en los dos botones (`main.py`, líneas 322 y 545) y no pasa por `locale.py`.
- El estado arranca con "⏳ Starting server…". El usuario no ha pedido un servidor; ha abierto un programa de subtítulos. Si el modelo aún no está listo, el texto debe decir eso y qué hacer si falla.
- Los avisos del log empiezan por ⚠️, ✓, ✗ o →. El símbolo no dice la acción, y el separador de log es una línea de cajas.
- El tutorial usa encabezados en mayúsculas ("GENERATE SUBTITLES TAB"). La skill trata las mayúsculas de etiqueta como un tic de plantilla, y aquí además gritan secciones de un texto de ayuda.

Cambio de copy, en los dos idiomas:

| Ahora | Propuesto |
| --- | --- |
| Input video *: | Vídeo |
| Output file *: | Archivo de subtítulos |
| No target | Dejar el idioma original |
| Translate / Convert | Traducir subtítulos, o Convertir formato si el checkbox está activo |
| Convert only (…) | Solo cambiar el formato |
| Default output dir: | Carpeta de los subtítulos |
| Clear console on Clear fields: | Vaciar el registro al limpiar los campos |
| Starting server… | Preparando el modelo de voz… |
| Pre-filled Tab 4 input | Audio listo para transcribir |
| Cancel | Cancelar |

Los campos obligatorios se dicen una vez, junto al botón, cuando falte algo: "Elige un vídeo para generar los subtítulos." El aviso de error dice qué falló y el siguiente paso, sin disculparse y sin emoji.

### 5. Generar esconde el tiempo y muestra el registro antes de que haya trabajo

El reloj `00:00:00` y la barra nacen ocultos, debajo del log. Mientras no hay vídeo, la mitad izquierda es un cuadro de Courier vacío. El tiempo es lo único que cambia durante una transcripción larga, y queda en el mismo estilo que una etiqueta secundaria.

Cambio: la franja de subtítulo y el reloj ocupan el centro en cuanto empieza el trabajo. Antes de eso, el mismo sitio dice la única acción posible: elegir un vídeo. El registro queda debajo, más bajo, y no compite con el reloj.

### 6. Ajustes mezcla el aspecto del programa con el aspecto del subtítulo

El panel de preferencias pone en la misma lista el modo claro/oscuro, el idioma de la interfaz, la carpeta, la fuente del subtítulo, dos muestras de color, la ruta del archivo de configuración y el interruptor del registro. "Subtitle Style" es otro rótulo encima del contenido, en el peso del cuerpo.

Cambio: dos grupos con un título de sección cada uno. "Programa": tema, idioma, carpeta. "Subtítulo en pantalla": familia, tamaño, color del texto, color del contorno, y una línea de ejemplo con esa fuente ("Así se verá el subtítulo."). La ruta del archivo de configuración pasa al final, en texto secundario, con "Abrir carpeta".

## Dirección visual

### Primer pase, descartado

La primera idea fue una sala de edición: fondo casi negro y un verde de forma de onda en el botón y en la barra. Es el aspecto por defecto de cualquier herramienta de vídeo, y es el mismo que ya tienen Ocean Dark (`#64FFDA`) y Emerald (`#2ECC71`). La skill pide no gastar el hueco libre en ese patrón. Tampoco sirve una página crema con un acento terracota: Sunset ya está al lado de ese cliché, y no describe un archivo de subtítulos.

### Qué se cambió y por qué

Se queda un solo gesto. Todo lo demás es quieto. El gesto es una franja de subtítulo: una línea en la fuente que el usuario eligió para el archivo, sobre una banda oscura, con el tiempo a la izquierda en un ámbar de código de tiempo. El ámbar no pinta botones, tarjetas ni fondos. El verde ácido y el azul Material salen del camino del estado normal.

### Color

Seis tokens, para el tema de trabajo:

- Noche `#161410` — fondo de la ventana. Cálido, para que no sea el negro teñido `#111`.
- Grafito `#2A2724` — campos y la banda donde se lee el subtítulo.
- Texto `#F4F1E8` — texto principal y la línea de subtítulo. Es el color de un subtítulo quemado, no el fondo de la página.
- Tiempo `#D6A15A` — solo el reloj y la barra mientras el trabajo corre. No es el terracota `#D97757`.
- Niebla `#A39A90` — etiquetas secundarias y ayuda.
- Falla `#C45B52` — error y cancelar, con texto `#F4F1E8` encima.

Hecho usa Niebla en claro, no un verde de éxito genérico. El estado "listo" lo dice la frase "Subtítulo guardado" y la línea dentro de la franja.

### Tipo

- Controles: una familia de interfaz ya instalada. En Windows, Segoe UI. No hace falta una segunda familia para títulos.
- Subtítulo: la familia de Ajustes (hoy Arial por defecto), solo en la franja de ejemplo y en la línea que se muestra al terminar.
- Reloj: la familia de controles, 28 px, cifras estables. No Courier.
- Cuerpo 14 px, secciones 18 px. Peso semibold solo en el botón primario y en el título de sección, también en oscuro.

Las líneas de ayuda no pasan de unos 80 caracteres. El registro puede ser más estrecho y seguir en una monoespaciada, porque es un registro, no una etiqueta.

### Layout

Alineado a la izquierda. El centro se reserva para la línea de subtítulo dentro de su franja, igual que un subtítulo se centra en el fotograma. No se justifica nada.

```
+------------------------------------------------------------------+
| Generar          Traducir un archivo                            |
+------------------------------------------------------------------+
| Vídeo                                                            |
| [ ruta del vídeo.............................. ] [ Elegir ]      |
| Archivo de subtítulos                                            |
| [ ruta del .srt............................... ] [ Guardar ]     |
| Idioma hablado [ Detectar ]   Idioma del subtítulo [ Original ]  |
| Formato [ SRT ]                                                  |
|                                                                  |
| +--------------------------------------------------------------+ |
| | 00:12:04                                                     | |
| |              así se lee una línea de subtítulo              | |
| +--------------------------------------------------------------+ |
| [ Generar subtítulos ]                                           |
| Registro                                                         |
| [ mensajes del trabajo......................................... ]|
+------------------------------------------------------------------+
```

Con el modo paso a paso, la franja de arriba se sustituye por la secuencia, porque ahí la numeración informa:

```
1 Extraer audio    2 Transcribir    3 Traducir    4 Escribir archivo
[ Extraer ]        [ Transcribir ]  [ Traducir ]  [ Escribir ]
```

Traducir un archivo es la misma columna, con el subtítulo de entrada en lugar del vídeo, y sin la secuencia.

### Principio

La ventana es una mesa de rotulación, no un panel de control. Un elemento se recuerda: la línea de subtítulo con su tiempo. El resto se queda quieto, alineado a la izquierda, y cada palabra nombra lo que la persona va a obtener.

## Suelo de calidad, en escritorio

- Los botones Examinar y Guardar como miden 80 px (`BTN_WIDTH_BROWSE`). "Save as…" y "Guardar como…" no caben. El ancho tiene que seguir al texto, con un alto mínimo de 44 px, que el botón primario ya cumple.
- Cancelar, Guardar y Volver de Ajustes tienen que salir de `locale.py`, como el resto.
- Contraste: Texto sobre Noche, y Texto sobre Falla. El ámbar `#D6A15A` solo en trazos grandes (el reloj), no en cuerpo pequeño sobre Noche.
- El foco de teclado tiene que verse en el campo y en el botón. Hoy el estilo no lo define.
- No añadir movimiento de entrada. La barra de progreso es la única animación, y solo mientras hay un trabajo.
- Al estrechar por debajo del mínimo, la fila de idiomas pasa debajo de los archivos. No hace falta una versión móvil.

## Fuera de este informe

No se modifica `main.py`, `theme.py`, `styles.py` ni `locale.py`. El primer paso de implementación, cuando se pida, es la copy y el contraste de los botones. La franja de subtítulo y la reducción a dos pestañas van después, porque mueven la estructura.
