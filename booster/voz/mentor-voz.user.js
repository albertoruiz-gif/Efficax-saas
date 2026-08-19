// ==UserScript==
// @name         Mentor por voz — Efficax Booster
// @namespace    https://efficaxba.com
// @version      1.0.0
// @description  Microfono nativo para hablarle a Mentor en el chat de Odoo. Envio por palabra de cierre ("...Mentor" al final), nunca por soltar el microfono.
// @match        https://efficaxba-online.odoo.com/*
// @match        https://*.odoo.com/*
// @grant        none
// ==/UserScript==

/*
 * DISEÑO (acordado con Alberto, 18-ago-2026, 3 rondas de ajuste):
 *
 * - Boton de microfono junto al composer del chat de agentes (widget
 *   nativo de Odoo, discuss/ai_chat). Usa la Web Speech API del
 *   navegador (SpeechRecognition) — streaming en vivo, gratis, sin
 *   tocar el backend de Odoo. Funciona en Chrome/Edge; no en Firefox.
 *
 * - Odoo Online (SaaS) no acepta modulos custom, asi que esto se
 *   distribuye como userscript de Tampermonkey — 100% client-side,
 *   no requiere ningun cambio en el tenant de Odoo.
 *
 * - ENVIO POR PALABRA DE CIERRE, no por silencio ni por soltar el mic:
 *     "Mentor" es la UNICA palabra dicha hasta el momento -> vocativo,
 *       sigue escuchando (el usuario esta empezando a hablar).
 *     "Mentor" es la PRIMERA palabra pero hay mas despues -> vocativo,
 *       sigue escuchando ("Mentor, agendame una reunion...").
 *     "Mentor" es la ULTIMA palabra y hay al menos otra palabra antes
 *       -> CIERRE: se envia. Se quita solo el "Mentor" final del texto
 *       (Mentor nunca ve su propio nombre pegado al final). La palabra
 *       justo antes ("hazlo", "dale", "listo", "envialo", cualquiera)
 *       se deja tal cual — no se intenta adivinar si era un verbo de
 *       control o contenido real del mensaje.
 *     "Mentor" en medio de la frase, sin quedar al final -> no cierra,
 *       sigue escuchando ("...dile a Mentor que...").
 *
 * - Mic = interruptor (toque enciende, toque apaga), manos libres.
 *   APAGAR EL MIC NUNCA ENVIA — el texto queda escrito en el composer
 *   para corregir a mano o dar Enter. El envio siempre es una decision
 *   explicita (la palabra de cierre, o Enter manual).
 *
 * - Recordatorio: al activar el mic la primera vez (por sesion de
 *   pagina), un aviso breve explica la palabra de cierre. Si el mic se
 *   apaga sin haber cerrado nunca (o pasa mucho silencio sin cierre),
 *   se muestra otra vez.
 */
(function () {
  'use strict';

  const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
  const SILENCIO_RECORDATORIO_MS = 45000; // sin cierre en este tiempo -> recordar

  /** Analiza el texto acumulado y decide si hay que cerrar (enviar).
   * Exportada aparte de la captura de audio para poder probarla sola. */
  function analizarCierre(textoCompleto) {
    const texto = (textoCompleto || '').trim();
    if (!texto) return { cierra: false, mensaje: '' };

    const palabras = texto.split(/\s+/);
    const ultima = palabras[palabras.length - 1].replace(/[.,;:!?¡¿"']+$/g, '');
    const esMentor = /^mentor$/i.test(ultima);

    if (!esMentor) return { cierra: false, mensaje: texto };
    if (palabras.length === 1) return { cierra: false, mensaje: texto }; // solo "Mentor" -> vocativo, sigue

    // "Mentor" es la ultima palabra y hay algo antes -> cierre.
    // Se quita unicamente el "Mentor" final (con su puntuacion pegada).
    const sinCierre = texto.slice(0, texto.length - palabras[palabras.length - 1].length).trim();
    return { cierra: true, mensaje: sinCierre };
  }

  function crearBanner(texto, tipo) {
    let banner = document.getElementById('mentor-voz-banner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'mentor-voz-banner';
      banner.style.cssText = [
        'position:fixed', 'bottom:90px', 'right:24px', 'z-index:99999',
        'max-width:320px', 'padding:10px 14px', 'border-radius:10px',
        'font-size:13px', 'line-height:1.4', 'font-family:sans-serif',
        'box-shadow:0 2px 10px rgba(0,0,0,.15)', 'transition:opacity .2s',
      ].join(';');
      document.body.appendChild(banner);
    }
    const colores = {
      info: ['#FFF1E8', '#B03A00'],
      escuchando: ['#E8F5E9', '#1B5E20'],
      enviado: ['#E3F2FD', '#0D47A1'],
    };
    const [fondo, texto_color] = colores[tipo] || colores.info;
    banner.style.background = fondo;
    banner.style.color = texto_color;
    banner.textContent = texto;
    banner.style.opacity = '1';
    clearTimeout(banner._t);
    banner._t = setTimeout(() => { banner.style.opacity = '0'; }, 6000);
  }

  function encontrarComposer() {
    const ta = document.querySelector('.o-mail-Composer-input');
    if (!ta) return null;
    const composer = ta.closest('.o-mail-Composer');
    const btnEnviar = composer && composer.querySelector('button[title="Enviar"]');
    return ta && btnEnviar ? { ta, btnEnviar } : null;
  }

  function escribirEnComposer(ta, texto) {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(ta, texto);
    ta.dispatchEvent(new Event('input', { bubbles: true }));
  }

  /** Envia el mensaje ya escrito. Probado en vivo (18-ago-2026): el
   * "Enter" en el textarea SI dispara el envio de Odoo; un click()
   * simple o eventos de mouse sinteticos en el boton NO lo disparan de
   * forma confiable (Odoo filtra eventos no confiables en algunos
   * casos). Por eso el Enter va primero, y el click queda de respaldo. */
  function enviarMensaje() {
    const composerInfo = encontrarComposer();
    if (!composerInfo) return;
    composerInfo.ta.focus();
    composerInfo.ta.dispatchEvent(new KeyboardEvent('keydown', {
      key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true, cancelable: true,
    }));
    setTimeout(() => {
      const cf = encontrarComposer();
      if (cf && cf.ta.value.trim()) cf.btnEnviar.click(); // respaldo si el Enter no alcanzo
      crearBanner('Enviado a Mentor.', 'enviado');
    }, 300);
  }

  function inicializarMicrofono() {
    if (!SpeechRecognitionAPI) {
      console.warn('[Mentor por voz] Este navegador no soporta reconocimiento de voz.');
      return;
    }

    let recognition = null;
    let escuchando = false;
    let yaExplico = false;
    let huboAlgunCierre = false;
    let recordatorioTimer = null;
    let baseTexto = ''; // lo que ya habia en el composer antes de empezar a dictar

    function mostrarRecordatorio() {
      crearBanner('Cuando termines, di "hazlo Mentor" (o cualquier orden + Mentor al final) para enviar.', 'info');
    }

    function reprogramarRecordatorio() {
      clearTimeout(recordatorioTimer);
      recordatorioTimer = setTimeout(mostrarRecordatorio, SILENCIO_RECORDATORIO_MS);
    }

    function detener(envioPorCierre) {
      escuchando = false;
      clearTimeout(recordatorioTimer);
      if (recognition) { try { recognition.stop(); } catch (e) {} }
      actualizarBoton();
      if (!envioPorCierre) {
        crearBanner('Micrófono apagado. No se envió nada — revisa el texto o di la orden de nuevo.', 'info');
      }
    }

    function manejarResultado(event) {
      const composerInfo = encontrarComposer();
      if (!composerInfo) return;
      let interinos = '';
      let finales = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finales += t + ' ';
        else interinos += t;
      }
      if (finales) {
        baseTexto = (baseTexto + ' ' + finales).trim();
      }
      const textoVivo = (baseTexto + ' ' + interinos).trim();
      escribirEnComposer(composerInfo.ta, textoVivo);
      reprogramarRecordatorio();

      if (finales) {
        const { cierra, mensaje } = analizarCierre(baseTexto);
        if (cierra) {
          huboAlgunCierre = true;
          escribirEnComposer(composerInfo.ta, mensaje);
          detener(true);
          setTimeout(() => enviarMensaje(), 50);
        }
      }
    }

    function iniciar() {
      const composerInfo = encontrarComposer();
      if (!composerInfo) {
        crearBanner('Abre el chat de Mentor primero.', 'info');
        return;
      }
      baseTexto = '';
      recognition = new SpeechRecognitionAPI();
      recognition.lang = 'es-PE';
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.onresult = manejarResultado;
      recognition.onerror = (e) => {
        if (e.error === 'no-speech') return; // silencio normal, no es error real
        crearBanner('Error de micrófono: ' + e.error, 'info');
        detener(false);
      };
      recognition.onend = () => {
        if (escuchando) { try { recognition.start(); } catch (e) {} } // se reinicia solo (Chrome lo corta cada rato)
      };
      recognition.start();
      escuchando = true;
      actualizarBoton();
      crearBanner('Escuchando… habla con Mentor.', 'escuchando');
      if (!yaExplico) { mostrarRecordatorio(); yaExplico = true; }
      reprogramarRecordatorio();
    }

    let botonMic = null;
    function actualizarBoton() {
      if (!botonMic) return;
      botonMic.textContent = escuchando ? '🔴' : '🎙️';
      botonMic.title = escuchando ? 'Escuchando… clic para apagar (no envía)' : 'Hablarle a Mentor';
    }

    function insertarBoton() {
      const composerInfo = encontrarComposer();
      if (!composerInfo || document.getElementById('mentor-voz-mic')) return;
      const btn = document.createElement('button');
      btn.id = 'mentor-voz-mic';
      btn.type = 'button';
      btn.style.cssText = 'border:none;background:transparent;font-size:18px;cursor:pointer;padding:4px 8px;';
      btn.textContent = '🎙️';
      btn.title = 'Hablarle a Mentor';
      btn.addEventListener('click', () => {
        if (escuchando) { huboAlgunCierre = false; detener(false); }
        else iniciar();
      });
      composerInfo.btnEnviar.parentElement.insertBefore(btn, composerInfo.btnEnviar);
      botonMic = btn;
      actualizarBoton();
    }

    // El composer de Odoo se monta/desmonta segun se abra el chat -> reintentar.
    setInterval(insertarBoton, 1000);
  }

  if (document.readyState === 'complete') inicializarMicrofono();
  else window.addEventListener('load', inicializarMicrofono);

  // Expuesto para pruebas automatizadas (ver mentor-voz.test.js).
  window.__mentorVoz = { analizarCierre };
})();
