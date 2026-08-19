/* Test de la funcion pura de deteccion de cierre (mentor-voz.user.js).
 * Corre con node directo (sin dependencias): node mentor-voz.test.js
 *
 * Los 8 casos replican EXACTAMENTE la prueba en vivo hecha el
 * 18-ago-2026 contra el chat real de Mentor (inyeccion via javascript
 * tool + confirmacion de que el mensaje llego limpio al canal). Este
 * test fija ese comportamiento para que un cambio futuro no lo rompa
 * sin darse cuenta. */

// Copia minima de la funcion (el archivo real es un IIFE sin exports;
// se mantiene identica a proposito -- si difiere, hay que sincronizar).
function analizarCierre(textoCompleto) {
  const texto = (textoCompleto || '').trim();
  if (!texto) return { cierra: false, mensaje: '' };
  const palabras = texto.split(/\s+/);
  const ultima = palabras[palabras.length - 1].replace(/[.,;:!?¡¿"']+$/g, '');
  const esMentor = /^mentor$/i.test(ultima);
  if (!esMentor) return { cierra: false, mensaje: texto };
  if (palabras.length === 1) return { cierra: false, mensaje: texto };
  const sinCierre = texto.slice(0, texto.length - palabras[palabras.length - 1].length).trim();
  return { cierra: true, mensaje: sinCierre };
}

const casos = [
  ['Mentor', false, 'Mentor'],
  ['Mentor, agendame una reunion con Juan el viernes a las tres', false, 'Mentor, agendame una reunion con Juan el viernes a las tres'],
  ['agendame una reunion con Juan el viernes a las tres, hazlo Mentor', true, 'agendame una reunion con Juan el viernes a las tres, hazlo'],
  ['agendame una reunion con Juan el viernes a las tres, dale Mentor', true, 'agendame una reunion con Juan el viernes a las tres, dale'],
  ['agendame una reunion con Juan el viernes a las tres, listo Mentor', true, 'agendame una reunion con Juan el viernes a las tres, listo'],
  ['mejor dile a Mentor que revise el contrato primero', false, 'mejor dile a Mentor que revise el contrato primero'],
  ['registra el contrato con Prueba SAC, semaforo verde, envialo Mentor.', true, 'registra el contrato con Prueba SAC, semaforo verde, envialo'],
  ['MENTOR', false, 'MENTOR'], // mayusculas, solo la palabra -> vocativo
  ['', false, ''],
];

let fallos = 0;
for (const [texto, cierraEsperado, mensajeEsperado] of casos) {
  const r = analizarCierre(texto);
  const ok = r.cierra === cierraEsperado && r.mensaje === mensajeEsperado;
  if (!ok) {
    fallos++;
    console.error('FALLO:', JSON.stringify(texto), '-> obtuvo', JSON.stringify(r), 'esperaba', { cierra: cierraEsperado, mensaje: mensajeEsperado });
  }
}

if (fallos === 0) {
  console.log(`OK: ${casos.length}/${casos.length} casos pasaron (mismos casos probados en vivo el 18-ago-2026).`);
  process.exit(0);
} else {
  console.error(`${fallos}/${casos.length} casos fallaron.`);
  process.exit(1);
}
