"""Genera el icono de app de Booster a partir del SVG real que Alberto
proveyó (`efficax_letter_b_dynamic_speed.svg`, guardado como referencia en
este mismo directorio) -- reconstruido con Pillow porque este entorno no
tiene un renderizador de SVG nativo disponible (cairosvg requiere la
libreria nativa libcairo, no instalable aquí). Las coordenadas de abajo
son una copia EXACTA de los `<path>`/`<rect>`/`<circle>` del SVG
original, no una reinterpretación a mano -- ver `efficax_letter_b_dynamic_speed.svg`
en este directorio para comparar.

Estilo pedido por Alberto (17-ago-2026): igual a como se ve el icono de
Efficax en la pantalla de un celular -- tile oscuro redondeado, con
BORDE NARANJA (para distinguir Booster de Efficax a simple vista).

Reproducible: correr este script regenera `icono_booster_b.png` desde
cero, no es un archivo editado a mano en un editor de imágenes.
"""
from PIL import Image, ImageDraw, ImageFilter

NARANJA = (255, 85, 0, 255)  # #FF5500, el mismo naranja del SVG original
NEGRO_TILE = (13, 13, 13, 255)  # #0D0D0D, fondo oscuro del tile
BORDE_NARANJA = (255, 106, 0, 255)  # #FF6A00, naranja de marca (brand book) para el borde

ESCALA = 4  # supersample para anti-aliasing, se reduce al final
LADO_FINAL = 512


def bezier_cubico(p0, p1, p2, p3, pasos=40):
    puntos = []
    for i in range(pasos + 1):
        t = i / pasos
        mt = 1 - t
        x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
        y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
        puntos.append((x, y))
    return puntos


def trazo_grueso(draw, puntos, ancho, color):
    draw.line(puntos, fill=color, width=ancho, joint="curve")
    radio = ancho / 2
    for p in (puntos[0], puntos[-1]):
        draw.ellipse([p[0] - radio, p[1] - radio, p[0] + radio, p[1] + radio], fill=color)


def construir_glifo_b(tam):
    """Dibuja la letra B (sistema de barras/puntos del SVG real de Alberto)
    sobre un lienzo cuadrado de `tam` px, viewBox original 0-420 x 0-400."""
    factor = tam / 420.0
    img = Image.new("RGBA", (tam, tam), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    ancho_trazo = round(23 * factor)

    def esc(p):
        return (p[0] * factor, p[1] * factor)

    # Path 1: M185,75 L255,75 C335,75 335,175 255,175 L185,175
    seg1 = [esc((185, 75)), esc((255, 75))]
    seg1 += bezier_cubico(esc((255, 75)), esc((335, 75)), esc((335, 175)), esc((255, 175)))
    seg1 += [esc((185, 175))]
    trazo_grueso(draw, seg1, ancho_trazo, NARANJA)

    # Path 2: M255,175 C345,175 345,275 260,275 L175,275
    seg2 = bezier_cubico(esc((255, 175)), esc((345, 175)), esc((345, 275)), esc((260, 275)))
    seg2 += [esc((175, 275))]
    trazo_grueso(draw, seg2, ancho_trazo, NARANJA)

    # Barras (rects redondeados) y puntos (circles), copiados del SVG.
    rects = [
        (135, 63.5, 35, 23),
        (105, 113.5, 58, 23),
        (135, 163.5, 35, 23),
        (95, 213.5, 58, 23),
    ]
    for x, y, w, h in rects:
        x0, y0 = esc((x, y))
        x1, y1 = esc((x + w, y + h))
        radio = (11.5) * factor
        draw.rounded_rectangle([x0, y0, x1, y1], radius=radio, fill=NARANJA)

    circulos = [(145, 275, 11.5), (255, 175, 11.5)]
    for cx, cy, r in circulos:
        cx_, cy_ = esc((cx, cy))
        r_ = r * factor
        draw.ellipse([cx_ - r_, cy_ - r_, cx_ + r_, cy_ + r_], fill=NARANJA)

    return img


def construir_icono():
    tam_render = LADO_FINAL * ESCALA
    lienzo = Image.new("RGBA", (tam_render, tam_render), (0, 0, 0, 0))

    # Tile redondeado oscuro (mismo look que un icono de app real: fondo
    # solido, esquinas redondeadas, borde naranja para distinguirse).
    radio_tile = round(tam_render * 0.22)
    grosor_borde = round(tam_render * 0.04)  # 18-ago-2026: mas ancho a pedido de Alberto (antes 0.018)
    tile = Image.new("RGBA", (tam_render, tam_render), (0, 0, 0, 0))
    draw_tile = ImageDraw.Draw(tile)
    draw_tile.rounded_rectangle(
        [0, 0, tam_render - 1, tam_render - 1], radius=radio_tile, fill=NEGRO_TILE
    )
    draw_tile.rounded_rectangle(
        [grosor_borde // 2, grosor_borde // 2, tam_render - 1 - grosor_borde // 2, tam_render - 1 - grosor_borde // 2],
        radius=radio_tile,
        outline=BORDE_NARANJA,
        width=grosor_borde,
    )
    lienzo.alpha_composite(tile)

    # Glifo B centrado, con margen interno (padding) para que no toque el borde.
    padding_pct = 0.20
    tam_glifo = round(tam_render * (1 - 2 * padding_pct))
    glifo = construir_glifo_b(tam_glifo)

    # Alto real del glifo es 400/420 del ancho (viewBox 420x400) -- se
    # centra verticalmente dentro del area del glifo.
    alto_glifo_real = round(tam_glifo * (400 / 420))
    offset_y_extra = (tam_glifo - alto_glifo_real) // 2
    pos_x = (tam_render - tam_glifo) // 2
    pos_y = (tam_render - tam_glifo) // 2 + offset_y_extra // 2

    # Resplandor suave detras del glifo (imita el filtro de glow del SVG).
    resplandor = glifo.copy()
    resplandor = resplandor.filter(ImageFilter.GaussianBlur(radius=tam_render * 0.012))
    lienzo.alpha_composite(resplandor, (pos_x, pos_y))
    lienzo.alpha_composite(glifo, (pos_x, pos_y))

    final = lienzo.resize((LADO_FINAL, LADO_FINAL), Image.LANCZOS)
    return final


if __name__ == "__main__":
    icono = construir_icono()
    salida = "icono_booster_b.png"
    icono.save(salida)
    print("Guardado:", salida, icono.size)
