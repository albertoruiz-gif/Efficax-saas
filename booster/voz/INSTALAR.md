# Mentor por voz — instalación (2 minutos, una sola vez)

Micrófono nativo para hablarle a Mentor en el chat de Odoo. Escuchas en
vivo, y cuando terminas dices **"...Mentor"** al final (por ejemplo
*"hazlo Mentor"*, *"dale Mentor"*, *"listo Mentor"*) para enviar. Apagar
el micrófono nunca envía nada por accidente.

Probado en vivo el 18-ago-2026 contra el chat real de Mentor Efficax
(piloto): escritura en tiempo real, detección de cierre, limpieza del
"Mentor" final y envío confirmados funcionando.

## Por qué un instalable y no algo "ya puesto" en Odoo

Odoo Online (SaaS, como el tenant de Efficax) no permite subir módulos
propios — solo Odoo.sh o instalaciones propias lo permiten. La única
forma de agregar el micrófono sin tocar el backend de Odoo es un
**userscript**: un pequeño script que corre en tu propio navegador,
sobre la página de Odoo que ya usas normalmente. No cambia nada en el
servidor, no lo ve nadie más que no lo instale.

## Instalación

1. Instala la extensión **Tampermonkey** en Chrome o Edge:
   https://chromewebstore.google.com/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo
2. Clic en el ícono de Tampermonkey → **Crear un script nuevo**.
3. Borra el contenido de ejemplo y pega el contenido completo de
   [`mentor-voz.user.js`](mentor-voz.user.js) (este mismo folder).
4. Ctrl+S para guardar.
5. Abre (o recarga) `efficaxba-online.odoo.com` y entra al chat de
   Mentor. Vas a ver un ícono 🎙️ junto al botón de enviar.

## Uso

1. Clic en 🎙️ — empieza a escuchar (el ícono cambia a 🔴).
2. Habla con calma, con pausas si necesitas pensar — el texto va
   apareciendo en el cuadro de mensaje mientras hablas.
3. Cuando termines, remata la frase con **"...Mentor"**:
   *"...agéndame la reunión el viernes a las 3, hazlo Mentor"*.
4. El "Mentor" final desaparece del texto y se envía solo.
5. Si quieres apagar el micrófono sin enviar (te arrepentiste, o vas a
   corregir algo a mano), clic de nuevo en 🔴 — el texto queda escrito,
   nada se envía.

## Notas

- Funciona en **Chrome y Edge**. No funciona en Firefox (esa API de voz
  no la soporta).
- La transcripción la hace el propio navegador (motor de Google) — no
  pasa por los servidores de Efficax ni de Odoo.
- Si la página de Mentor recarga o cierras el chat, vuelve a activar el
  micrófono con un clic — el script lo detecta solo.
