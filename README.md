# Foto de producto

¿Vendés algo por internet y sacaste la foto con el celular? Esta aplicación la deja lista para publicar en tu tienda online o en tus redes sociales: le saca el fondo, centra el producto, mejora la luz y los colores, la adapta al tamaño que pide cada sitio y hace que pese lo justo para subirla sin problemas.

Funciona en tu computadora. No hace falta crear una cuenta y tus fotos no se suben a ningún lado.

## Qué podés hacer con ella

- **Quitar el fondo** y dejar el producto sobre blanco, como en las tiendas profesionales.
- **Centrar el producto**, con más o menos espacio alrededor.
- **Mejorar la luz y el color**: más o menos brillo, más o menos contraste, aclarar las zonas oscuras y corregir los colores cuando la foto salió amarillenta o azulada.
- **Elegir dónde vas a publicar** y que la foto quede con el tamaño exacto: Mercado Libre, Tienda Nube, Instagram (cuadrada o vertical) e Historias o Reels.
- **Dar el toque final**: completar con bordes blancos o recortar lo que sobra, hacer la imagen más nítida y elegir cuánto pesa el archivo (liviano, normal o máxima calidad).
- **Ver el resultado antes de guardar** y descargar la foto lista.
- **Guardar tus trabajos** para volver a verlos o descargarlos más tarde.

## Cómo instalarla (una sola vez)

1. **Instalá Python** desde https://www.python.org/downloads/ (versión 3.10 o más nueva). Durante la instalación, marcá la casilla **"Add Python to PATH"**.
2. **Descargá esta carpeta** del proyecto en tu computadora (en GitHub: botón verde *Code* → *Download ZIP*, y descomprimila).
3. Abrí la carpeta `backend` y, en la barra de direcciones del explorador de archivos, escribí `cmd` y apretá Enter. Se abre una ventana negra.
4. Copiá y pegá estas dos líneas, una por vez, apretando Enter después de cada una (la segunda tarda unos minutos):

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## Cómo abrirla (cada vez que quieras usarla)

1. Abrí la ventana negra como en el paso 3 anterior (dentro de la carpeta `backend`).
2. Pegá esta línea y apretá Enter:

```
.venv\Scripts\uvicorn app.main:app --port 8765
```

3. Abrí tu navegador (Chrome, Edge, Firefox…) y entrá a **http://localhost:8765**
4. Cuando termines, cerrá la ventana negra para apagar la aplicación.

## Cómo usarla, paso a paso

1. **Elegí tu foto.** Arrastrala a la pantalla o buscala en tu computadora.
2. **Quitar el fondo (opcional).**
   - Marcá *quitar el fondo* para que el producto quede sobre blanco.
   - Marcá *centrar* si querés el producto en el medio; podés elegir poco, normal o mucho espacio alrededor. Se puede centrar sin quitar el fondo.
   - Si el fondo no se quita bien, **dibujá una línea alrededor del producto** con el mouse, sin apuro y sin que sea perfecta: la aplicación la alisa sola. Después podés arrastrar los puntos que aparecen para corregirla, tocar la línea para agregar un punto, o hacer doble clic en un punto para borrarlo. El botón de borrar el contorno te deja empezar de nuevo.
3. **Luz y color (opcional).** Movés los controles de brillo y contraste, activás *aclarar zonas oscuras* o *colores naturales*, y ves el cambio en el momento. Hay un botón para volver todo a como estaba.
4. **¿Dónde vas a publicar?** Elegí tu tienda o red social. La aplicación sabe qué tamaño necesita cada una.
5. **Terminación.**
   - Elegí si completar con bordes blancos o recortar la foto. Si recortás, con los controles de posición elegís qué parte conservar.
   - Elegí cuánta nitidez querés: nada, poco o mucho.
   - Elegí el peso del archivo: liviano (carga rápido), normal o máxima calidad.
6. **Guardar y descargar.** Descargá la foto ya lista. También queda guardada en la aplicación para que la encuentres después, y desde ahí la podés borrar si ya no la querés.

## Consejos para mejores resultados

- Sacá la foto con buena luz y con el producto bien a la vista.
- Un fondo liso y que no se parezca al color del producto ayuda mucho a quitarlo.
- Si el fondo no se quita como querés, usá el contorno a mano: es la forma más segura.
- Quitar el fondo puede tardar unos segundos cada vez que cambiás algo.
- Si el programa te avisa que no pudo bajar el peso sin arruinar la foto, la guardó con la mejor calidad posible; probá con el peso *normal*.

## ¿Algo no funciona?

- **"python no se reconoce como un comando":** reinstalá Python marcando *"Add Python to PATH"*.
- **La página no abre:** fijate que la ventana negra siga abierta y que haya dicho que el servidor está andando.
- **Dice que el puerto está ocupado:** cerrá otras ventanas negras que tengas abiertas con la aplicación y volvé a abrirla.
