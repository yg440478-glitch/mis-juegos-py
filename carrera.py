"""Carreras 1 vs 1: el jugador compite contra un rival controlado por IA.
Requiere Python 3.13+ y pygame. Todos los gráficos y efectos de sonido se generan
con código; no necesita imágenes ni archivos de audio externos.
"""
from __future__ import annotations

import math
import random
import sys
from array import array

import pygame

# ---------------------------- Configuración ----------------------------
ANCHO, ALTO = 800, 800
FPS = 60
META = 2800.0  # metros virtuales de carrera
ESCALA_M = 1.55
Y_JUGADOR = 625
CARRILES_X = (225, 400, 575)
ANCHO_CARRO, ALTO_CARRO = 48, 76

# Colores
BLANCO = (246, 248, 255)
NEGRO = (12, 16, 24)
PANEL = (19, 27, 42)
PANEL_BORDE = (51, 68, 91)
VERDE = (34, 120, 58)
VERDE_OSCURO = (25, 88, 44)
ASFALTO = (48, 52, 61)
ASFALTO_CLARO = (64, 69, 78)
AZUL = (38, 151, 255)
AZUL_CLARO = (126, 213, 255)
ROJO = (244, 72, 77)
ROJO_CLARO = (255, 160, 153)
AMARILLO = (255, 220, 73)
NARANJA = (255, 148, 65)
MORADO = (177, 111, 245)
VERDE_NEON = (87, 237, 157)
GRIS = (177, 188, 204)

pygame.mixer.pre_init(frequency=22050, size=-16, channels=1, buffer=512)
pygame.init()
AUDIO_OK = False
try:
    if pygame.mixer.get_init() is None:
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    pygame.mixer.set_num_channels(12)
    AUDIO_OK = True
except pygame.error:
    AUDIO_OK = False

pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Carreras 1 vs 1 | Tú contra el computador")
reloj = pygame.time.Clock()
fuente_logo = pygame.font.SysFont("arial", 46, bold=True)
fuente_titulo = pygame.font.SysFont("arial", 33, bold=True)
fuente_grande = pygame.font.SysFont("arial", 28, bold=True)
fuente = pygame.font.SysFont("arial", 21, bold=True)
fuente_mediana = pygame.font.SysFont("arial", 17, bold=True)
fuente_chica = pygame.font.SysFont("arial", 14)

SONIDO_ACTIVO = True

def sonido_sintetico(freq: float, duracion: float, volumen: float = 0.4,
                     barrido: float = 0.0, ruido: float = 0.0):
    """Crea un sonido sencillo en memoria. Devuelve None si no hay audio."""
    if not AUDIO_OK:
        return None
    total = max(1, int(22050 * duracion))
    muestras = array("h")
    for i in range(total):
        t = i / 22050
        envolvente = min(1.0, t / 0.012) * max(0.0, 1.0 - t / duracion) ** 1.25
        fase = 2 * math.pi * (freq * t + 0.5 * barrido * t * t / duracion)
        valor = math.sin(fase) * (1 - ruido) + random.uniform(-1, 1) * ruido
        muestras.append(int(max(-1, min(1, valor * volumen * envolvente)) * 32767))
    try:
        return pygame.mixer.Sound(buffer=muestras.tobytes())
    except pygame.error:
        return None

SONIDOS = {
    "cambio": sonido_sintetico(470, 0.10, 0.34, barrido=180),
    "nitro": sonido_sintetico(150, 0.34, 0.42, barrido=760),
    "choque": sonido_sintetico(90, 0.30, 0.56, barrido=-25, ruido=0.58),
    "punto": sonido_sintetico(640, 0.16, 0.36, barrido=280),
    "inicio": sonido_sintetico(390, 0.27, 0.42, barrido=420),
    "victoria": sonido_sintetico(680, 0.45, 0.42, barrido=600),
}

def reproducir(nombre: str) -> None:
    if SONIDO_ACTIVO and AUDIO_OK and SONIDOS.get(nombre):
        try:
            SONIDOS[nombre].play()
        except pygame.error:
            pass

class Corredor:
    def __init__(self, nombre: str, color: tuple[int, int, int], carril: int,
                 velocidad: float, es_jugador: bool):
        self.nombre = nombre
        self.color = color
        self.carril = carril
        self.carril_visual = float(carril)
        self.distancia = 0.0
        self.velocidad = velocidad
        self.es_jugador = es_jugador
        self.nitro = 100.0
        self.choque_tiempo = 0.0
        self.inmunidad = 0.0
        self.cambios_ia = 0.0
        self.hits: set[int] = set()


def crear_obstaculos() -> list[dict]:
    """Crea tráfico a lo largo de la carrera dejando al menos un carril libre."""
    obstaculos: list[dict] = []
    distancia = 155.0
    identificador = 0
    while distancia < META - 100:
        carriles = [0, 1, 2]
        cantidad = 2 if random.random() < 0.28 else 1
        bloqueados = random.sample(carriles, cantidad)
        for carril in bloqueados:
            obstaculos.append({
                "id": identificador,
                "distancia": distancia + random.uniform(-10, 10),
                "carril": carril,
                "color": random.choice([ROJO, NARANJA, MORADO, (225, 228, 235)]),
                "tipo": random.choice(["auto", "auto", "camion"]),
            })
            identificador += 1
        distancia += random.uniform(135, 190)
    return obstaculos


def nueva_carrera() -> dict:
    return {
        "jugador": Corredor("TÚ", AZUL, 0, 160.0, True),
        "cpu": Corredor("COMPUTADOR", ROJO, 2, 174.0, False),
        "obstaculos": crear_obstaculos(),
        "desplazamiento": 0.0,
        "cuenta_atras": 3.2,
        "ganador": None,
        "mensaje_choque": 0.0,
        "anterior_ventaja": None,
        "nitro_previo": False,
    }


def dibujar_texto(texto: str, x: int, y: int, color=BLANCO,
                  tipografia=fuente, centro=False, superficie=None):
    destino = superficie or pantalla
    imagen = tipografia.render(str(texto), True, color)
    rect = imagen.get_rect()
    if centro:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    destino.blit(imagen, rect)
    return rect


def panel(rect, color=PANEL, borde=PANEL_BORDE, radio=15, ancho=2):
    pygame.draw.rect(pantalla, color, rect, border_radius=radio)
    if borde:
        pygame.draw.rect(pantalla, borde, rect, width=ancho, border_radius=radio)


def dibujar_arbol(x: int, y: int, escala: float = 1.0):
    pygame.draw.ellipse(pantalla, VERDE_OSCURO,
                       (int(x-17*escala), int(y+9*escala), int(36*escala), int(11*escala)))
    pygame.draw.rect(pantalla, (115, 81, 49),
                     (int(x-3*escala), int(y), max(3, int(6*escala)), max(5, int(19*escala))), border_radius=2)
    pygame.draw.circle(pantalla, (24, 99, 49), (x, y), max(5, int(15*escala)))
    pygame.draw.circle(pantalla, (45, 148, 65), (int(x-4*escala), int(y-5*escala)), max(4, int(9*escala)))


def dibujar_pista(distancia: float):
    pantalla.fill(VERDE)
    # Césped y decoración animada.
    for i, x in enumerate((52, 94, 706, 750, 68, 730, 105, 690)):
        base = (i * 113 + 35) % (ALTO + 80)
        y = int((base + distancia * 1.6) % (ALTO + 80) - 40)
        dibujar_arbol(x, y, 0.72 if i % 2 else 0.88)
    pygame.draw.rect(pantalla, (214, 211, 187), (126, 0, 548, ALTO))
    pygame.draw.rect(pantalla, ASFALTO, (137, 0, 526, ALTO))
    pygame.draw.rect(pantalla, (34, 38, 45), (144, 0, 512, ALTO))
    # Bordes rojo/blanco desplazándose.
    offset = int(distancia * 1.7) % 58
    for y in range(-58, ALTO + 58, 58):
        py = y + offset
        color = BLANCO if (y // 58) % 2 == 0 else ROJO
        pygame.draw.rect(pantalla, color, (137, py, 8, 29))
        pygame.draw.rect(pantalla, color, (655, py, 8, 29))
    # Líneas separadoras de carril.
    desplazamiento = int(distancia * 1.6) % 84
    for y in range(-84, ALTO + 84, 84):
        py = y + desplazamiento
        for x in (312, 488):
            pygame.draw.rect(pantalla, (220, 223, 228), (x, py, 5, 42), border_radius=2)
    # Pequeñas marcas de goma.
    for y in range(120, ALTO, 200):
        py = int((y + distancia * 1.4) % ALTO)
        pygame.draw.line(pantalla, ASFALTO_CLARO, (160, py), (190, py+12), 2)


def dibujar_carro(x_centro: int, y: int, color, rival=False, nitro=False, invulnerable=False):
    x = int(x_centro)
    y = int(y)
    if y < -100 or y > ALTO + 100:
        return
    # Llama del nitro detrás del carro.
    if nitro:
        puntos = [(x-10, y+62), (x, y+91+random.randint(0, 8)), (x+10, y+62)]
        pygame.draw.polygon(pantalla, AMARILLO, puntos)
        pygame.draw.polygon(pantalla, AZUL_CLARO, [(x-5, y+63), (x, y+81), (x+5, y+63)])
    sombra = pygame.Rect(x-ANCHO_CARRO//2+4, y+5, ANCHO_CARRO, ALTO_CARRO)
    pygame.draw.rect(pantalla, (20, 24, 29), sombra, border_radius=11)
    # Llantas.
    for wx in (x-ANCHO_CARRO//2-2, x+ANCHO_CARRO//2-4):
        pygame.draw.rect(pantalla, NEGRO, (wx, y+13, 7, 17), border_radius=2)
        pygame.draw.rect(pantalla, NEGRO, (wx, y+47, 7, 17), border_radius=2)
    carro = pygame.Rect(x-ANCHO_CARRO//2, y, ANCHO_CARRO, ALTO_CARRO)
    pygame.draw.rect(pantalla, color, carro, border_radius=10)
    # Brillo lateral.
    pygame.draw.line(pantalla, (255, 255, 255), (x-17, y+13), (x-17, y+54), 2)
    # Parabrisas y ventana trasera.
    pygame.draw.polygon(pantalla, (153, 222, 255), [(x-14, y+13), (x+14, y+13), (x+11, y+30), (x-11, y+30)])
    pygame.draw.polygon(pantalla, (85, 149, 190), [(x-11, y+43), (x+11, y+43), (x+14, y+54), (x-14, y+54)])
    pygame.draw.line(pantalla, (222, 243, 255), (x, y+14), (x, y+29), 2)
    # Luces.
    pygame.draw.rect(pantalla, AMARILLO, (x-16, y+3, 10, 5), border_radius=2)
    pygame.draw.rect(pantalla, AMARILLO, (x+6, y+3, 10, 5), border_radius=2)
    pygame.draw.rect(pantalla, ROJO_CLARO, (x-15, y+65, 9, 4), border_radius=1)
    pygame.draw.rect(pantalla, ROJO_CLARO, (x+6, y+65, 9, 4), border_radius=1)
    if invulnerable:
        pygame.draw.rect(pantalla, BLANCO, carro.inflate(8, 8), width=2, border_radius=12)
    placa = "TÚ" if not rival else "IA"
    rotulo = fuente_chica.render(placa, True, BLANCO)
    rect = rotulo.get_rect(center=(x, y+36))
    # placa pequeña opaca para que se vea la etiqueta
    pygame.draw.rect(pantalla, (20, 27, 39), rect.inflate(8, 5), border_radius=4)
    pantalla.blit(rotulo, rect)


def dibujar_obstaculo(obs: dict, y: int):
    x = CARRILES_X[obs["carril"]]
    if obs["tipo"] == "camion":
        ancho, alto = 55, 85
    else:
        ancho, alto = 45, 68
    rect = pygame.Rect(x-ancho//2+3, y+4, ancho, alto)
    pygame.draw.rect(pantalla, (23, 25, 30), rect, border_radius=8)
    rect = pygame.Rect(x-ancho//2, y, ancho, alto)
    pygame.draw.rect(pantalla, obs["color"], rect, border_radius=8)
    pygame.draw.rect(pantalla, (178, 224, 246), (x-ancho//2+7, y+10, ancho-14, 16), border_radius=4)
    pygame.draw.rect(pantalla, (63, 75, 91), (x-ancho//2+8, y+34, ancho-16, 13), border_radius=3)
    pygame.draw.rect(pantalla, AMARILLO, (x-ancho//2+5, y+alto-8, 8, 4))
    pygame.draw.rect(pantalla, AMARILLO, (x+ancho//2-13, y+alto-8, 8, 4))


def barra_progreso(x: int, y: int, ancho: int, distancia: float, color, etiqueta: str):
    pygame.draw.rect(pantalla, (47, 58, 75), (x, y, ancho, 10), border_radius=5)
    relleno = int(ancho * max(0.0, min(1.0, distancia / META)))
    if relleno > 0:
        pygame.draw.rect(pantalla, color, (x, y, relleno, 10), border_radius=5)
    dibujar_texto(etiqueta, x, y-18, color, fuente_chica)


def dibujar_hud(jugador: Corredor, cpu: Corredor, mensaje: str = ""):
    # Cabecera compacta.
    pygame.draw.rect(pantalla, (13, 19, 31), (0, 0, ANCHO, 112))
    pygame.draw.line(pantalla, (54, 70, 92), (0, 111), (ANCHO, 111), 2)
    panel((16, 12, 224, 82), (24, 39, 59), AZUL, 13, 2)
    dibujar_texto("TÚ", 30, 20, AZUL_CLARO, fuente_mediana)
    dibujar_texto(f"{int(jugador.velocidad):3d} km/h", 30, 45, BLANCO, fuente_grande)
    panel((560, 12, 224, 82), (44, 30, 42), ROJO, 13, 2)
    dibujar_texto("COMPUTADOR", 575, 20, ROJO_CLARO, fuente_mediana)
    dibujar_texto(f"{int(cpu.velocidad):3d} km/h", 575, 45, BLANCO, fuente_grande)
    # Progreso al centro.
    panel((222, 12, 356, 82), (20, 29, 44), PANEL_BORDE, 13, 1)
    dibujar_texto("PROGRESO HACIA LA META", 400, 24, BLANCO, fuente_chica, centro=True)
    barra_progreso(250, 51, 300, jugador.distancia, AZUL, "TÚ")
    barra_progreso(250, 75, 300, cpu.distancia, ROJO, "IA")
    if mensaje:
        dibujar_texto(mensaje, 400, 132, AMARILLO, fuente_mediana, centro=True)


def cpu_pensar(cpu: Corredor, obstaculos: list[dict], dt: float, ventaja: float):
    """Elige carriles y velocidad según los peligros próximos."""
    cpu.cambios_ia -= dt
    peligros_por_carril = [9999.0, 9999.0, 9999.0]
    for obs in obstaculos:
        delante = obs["distancia"] - cpu.distancia
        if -20 < delante < 165:
            peligros_por_carril[obs["carril"]] = min(peligros_por_carril[obs["carril"]], delante)
    peligro_actual = peligros_por_carril[cpu.carril]
    if peligro_actual < 112 and cpu.cambios_ia <= 0:
        candidatos = [i for i in range(3) if peligros_por_carril[i] > 145]
        if candidatos:
            # Si va perdiendo, la IA intenta conservar carril despejado y ganar velocidad.
            nuevo = max(candidatos, key=lambda i: peligros_por_carril[i])
        else:
            nuevo = max(range(3), key=lambda i: peligros_por_carril[i])
        if nuevo != cpu.carril:
            cpu.carril = nuevo
            cpu.cambios_ia = 0.48
            reproducir("cambio")
    # El computador es competitivo, pero no conduce a velocidad máxima constante.
    objetivo = 205 + 7 * math.sin(cpu.distancia / 210.0)
    if ventaja < -120:
        objetivo += 5.0
    if peligros_por_carril[cpu.carril] < 48:
        objetivo = min(objetivo, 145)
    aceleracion = 27.0 if cpu.velocidad < objetivo else 17.0
    cpu.velocidad += max(-aceleracion*dt, min(aceleracion*dt, objetivo-cpu.velocidad))
    cpu.velocidad = max(95.0, min(225.0, cpu.velocidad))
    cpu.carril_visual += (cpu.carril - cpu.carril_visual) * min(1.0, dt * 9.5)


def procesar_choques(corredor: Corredor, obstaculos: list[dict], indice: str):
    for obs in obstaculos:
        if obs["id"] in corredor.hits:
            continue
        if obs["carril"] == corredor.carril and abs(obs["distancia"] - corredor.distancia) < 43:
            corredor.hits.add(obs["id"])
            corredor.velocidad = max(88.0, corredor.velocidad - 62.0)
            corredor.choque_tiempo = 0.75
            corredor.inmunidad = 0.9
            reproducir("choque")
            return True
    return False


def dibujar_menu():
    pantalla.fill((12, 21, 34))
    # Rayos gráficos de fondo.
    for i in range(14):
        x = i * 67 - 100
        pygame.draw.line(pantalla, (20, 45, 62), (x, 0), (x+250, ALTO), 2)
    panel((70, 70, 660, 650), (18, 29, 45), (55, 86, 117), 26, 2)
    dibujar_texto("CARRERAS", 400, 145, BLANCO, fuente_logo, centro=True)
    dibujar_texto("TÚ  VS  COMPUTADOR", 400, 203, AZUL_CLARO, fuente_titulo, centro=True)
    # Carros grandes.
    dibujar_carro(285, 260, AZUL, rival=False)
    dibujar_carro(515, 260, ROJO, rival=True)
    pygame.draw.line(pantalla, AMARILLO, (305, 355), (495, 355), 3)
    dibujar_texto("2800 METROS HASTA LA META", 400, 385, AMARILLO, fuente, centro=True)
    panel((126, 430, 548, 132), (25, 42, 59), (52, 82, 105), 18, 1)
    dibujar_texto("CONTROLES", 400, 453, VERDE_NEON, fuente, centro=True)
    dibujar_texto("← / →   Cambiar de carril", 400, 484, BLANCO, fuente_mediana, centro=True)
    dibujar_texto("↑ acelerar  ·  ↓ frenar  ·  SHIFT turbo", 400, 511, BLANCO, fuente_mediana, centro=True)
    dibujar_texto("P pausar  ·  M sonido  ·  ESC menú", 400, 538, GRIS, fuente_chica, centro=True)
    panel((220, 594, 360, 65), (32, 110, 76), VERDE_NEON, 18, 2)
    dibujar_texto("PULSA ENTER PARA CORRER", 400, 626, BLANCO, fuente, centro=True)
    dibujar_texto("El computador conduce automáticamente. ¡Gánale!", 400, 682, GRIS, fuente_mediana, centro=True)
    pygame.display.flip()


def dibujar_pausa():
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    capa.fill((5, 9, 15, 205))
    pantalla.blit(capa, (0, 0))
    panel((175, 280, 450, 235), (19, 30, 46), (77, 111, 144), 24, 2)
    dibujar_texto("PAUSA", 400, 333, BLANCO, fuente_titulo, centro=True)
    dibujar_texto("P o ENTER: continuar", 400, 390, AZUL_CLARO, fuente, centro=True)
    dibujar_texto("R: reiniciar carrera   ·   ESC: menú", 400, 431, GRIS, fuente_mediana, centro=True)


def dibujar_resultado(ganador: str, jugador: Corredor, cpu: Corredor):
    capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    capa.fill((5, 9, 15, 218))
    pantalla.blit(capa, (0, 0))
    player_gana = ganador == "TÚ"
    color = VERDE_NEON if player_gana else ROJO_CLARO
    titulo = "¡GANASTE LA CARRERA!" if player_gana else "¡GANÓ EL COMPUTADOR!"
    panel((100, 245, 600, 315), (18, 31, 47), color, 26, 3)
    dibujar_texto(titulo, 400, 298, color, fuente_titulo, centro=True)
    dibujar_texto(f"Tu progreso: {int(min(META, jugador.distancia))} m", 400, 366, BLANCO, fuente, centro=True)
    dibujar_texto(f"Computador: {int(min(META, cpu.distancia))} m", 400, 404, BLANCO, fuente, centro=True)
    if player_gana:
        dibujar_texto("¡Excelente conducción!", 400, 451, AMARILLO, fuente, centro=True)
    else:
        dibujar_texto("Intenta acelerar y usar el nitro en rectas libres.", 400, 451, AMARILLO, fuente_mediana, centro=True)
    panel((205, 492, 390, 48), (37, 63, 87), (79, 119, 153), 13, 1)
    dibujar_texto("R: revancha     ENTER: menú", 400, 516, BLANCO, fuente_mediana, centro=True)


def main():
    global SONIDO_ACTIVO
    estado_app = "menu"
    carrera = None
    ejecutando = True
    mejor_tiempo = None
    motor_t = 0.0

    while ejecutando:
        dt = min(reloj.tick(FPS) / 1000.0, 0.04)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    if estado_app == "menu":
                        ejecutando = False
                    elif estado_app in ("jugando", "pausa", "resultado", "cuenta"):
                        estado_app = "menu"
                if evento.key == pygame.K_m:
                    SONIDO_ACTIVO = not SONIDO_ACTIVO
                    if AUDIO_OK and not SONIDO_ACTIVO:
                        pygame.mixer.stop()
                    elif SONIDO_ACTIVO:
                        reproducir("cambio")
                if estado_app == "menu" and evento.key in (pygame.K_RETURN, pygame.K_SPACE):
                    carrera = nueva_carrera()
                    estado_app = "cuenta"
                    reproducir("inicio")
                elif estado_app == "cuenta" and evento.key == pygame.K_p:
                    estado_app = "pausa"
                elif estado_app == "jugando":
                    if evento.key == pygame.K_p:
                        estado_app = "pausa"
                    elif evento.key in (pygame.K_LEFT, pygame.K_a):
                        jugador = carrera["jugador"]
                        if jugador.carril > 0:
                            jugador.carril -= 1
                            reproducir("cambio")
                    elif evento.key in (pygame.K_RIGHT, pygame.K_d):
                        jugador = carrera["jugador"]
                        if jugador.carril < 2:
                            jugador.carril += 1
                            reproducir("cambio")
                elif estado_app == "pausa":
                    if evento.key in (pygame.K_p, pygame.K_RETURN, pygame.K_SPACE):
                        estado_app = "jugando"
                    elif evento.key == pygame.K_r:
                        carrera = nueva_carrera()
                        estado_app = "cuenta"
                    elif evento.key == pygame.K_RETURN:
                        estado_app = "menu"
                elif estado_app == "resultado":
                    if evento.key == pygame.K_r:
                        carrera = nueva_carrera()
                        estado_app = "cuenta"
                        reproducir("inicio")
                    elif evento.key == pygame.K_RETURN:
                        estado_app = "menu"

        if estado_app == "menu":
            dibujar_menu()
            continue

        if carrera is None:
            carrera = nueva_carrera()

        jugador: Corredor = carrera["jugador"]
        cpu: Corredor = carrera["cpu"]
        obstaculos = carrera["obstaculos"]

        if estado_app == "cuenta":
            carrera["cuenta_atras"] -= dt
            if carrera["cuenta_atras"] <= 0:
                estado_app = "jugando"
                reproducir("inicio")
        elif estado_app == "jugando":
            teclas = pygame.key.get_pressed()
            nitro = bool(teclas[pygame.K_LSHIFT] or teclas[pygame.K_RSHIFT]) and jugador.nitro > 0
            jugador.choque_tiempo = max(0.0, jugador.choque_tiempo-dt)
            jugador.inmunidad = max(0.0, jugador.inmunidad-dt)
            cpu.choque_tiempo = max(0.0, cpu.choque_tiempo-dt)
            cpu.inmunidad = max(0.0, cpu.inmunidad-dt)

            # Control de acelerador y freno.
            if jugador.choque_tiempo <= 0:
                if teclas[pygame.K_UP] or teclas[pygame.K_w]:
                    jugador.velocidad += 38 * dt
                else:
                    jugador.velocidad -= 5 * dt
                if teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
                    jugador.velocidad -= 62 * dt
                if nitro:
                    jugador.velocidad += 22 * dt
                    jugador.nitro = max(0.0, jugador.nitro - 31 * dt)
                    if not carrera["nitro_previo"]:
                        reproducir("nitro")
                else:
                    jugador.nitro = min(100.0, jugador.nitro + 13 * dt)
                carrera["nitro_previo"] = nitro
            jugador.velocidad = max(85.0, min(295.0 if nitro else 245.0, jugador.velocidad))

            # Progreso en metros: km/h * segundos / 3.6.
            jugador.distancia += jugador.velocidad * dt / 3.6
            cpu_pensar(cpu, obstaculos, dt, jugador.distancia-cpu.distancia)
            cpu.distancia += cpu.velocidad * dt / 3.6
            jugador.carril_visual += (jugador.carril - jugador.carril_visual) * min(1.0, dt*12)
            carrera["desplazamiento"] += jugador.velocidad * dt * 0.72

            # Choques contra tráfico. Cada obstáculo afecta a cada coche una sola vez.
            if jugador.inmunidad <= 0:
                procesar_choques(jugador, obstaculos, "jugador")
            if cpu.inmunidad <= 0:
                procesar_choques(cpu, obstaculos, "cpu")

            # Si ambos corredores se cruzan en el mismo carril, hay choque entre autos.
            if (jugador.carril == cpu.carril
                    and abs(jugador.distancia - cpu.distancia) < 43
                    and jugador.inmunidad <= 0 and cpu.inmunidad <= 0):
                jugador.velocidad = max(88.0, jugador.velocidad - 36.0)
                cpu.velocidad = max(88.0, cpu.velocidad - 36.0)
                jugador.choque_tiempo = cpu.choque_tiempo = 0.55
                jugador.inmunidad = cpu.inmunidad = 1.0
                carriles_alternativos = [i for i in range(3) if i != jugador.carril]
                cpu.carril = max(carriles_alternativos, key=lambda i: abs(i-cpu.carril))
                cpu.cambios_ia = 0.65
                reproducir("choque")

            # Nitro/bonificación audible si se acerca la meta.
            if jugador.distancia >= META:
                jugador.distancia = META
                carrera["ganador"] = "TÚ"
                estado_app = "resultado"
                reproducir("victoria")
            elif cpu.distancia >= META:
                cpu.distancia = META
                carrera["ganador"] = "COMPUTADOR"
                estado_app = "resultado"

        # Dibujo de carrera, pausa y resultado.
        dibujar_pista(carrera["desplazamiento"])
        # Tráfico visible a partir de la posición del jugador.
        for obs in obstaculos:
            y = int(Y_JUGADOR - (obs["distancia"] - jugador.distancia) * ESCALA_M)
            if -100 < y < ALTO + 80:
                dibujar_obstaculo(obs, y)
        # El rival se coloca según la diferencia real de progreso.
        y_cpu = int(Y_JUGADOR - (cpu.distancia-jugador.distancia)*ESCALA_M)
        if -100 < y_cpu < ALTO + 90:
            dibujar_carro(int(CARRILES_X[int(round(cpu.carril_visual))]), y_cpu, ROJO, rival=True,
                          nitro=(cpu.velocidad > 218), invulnerable=(cpu.inmunidad > 0))
        dibujar_carro(int(CARRILES_X[int(round(jugador.carril_visual))]), Y_JUGADOR, AZUL,
                      nitro=(estado_app == "jugando" and carrera["nitro_previo"]),
                      invulnerable=(jugador.inmunidad > 0))

        # Línea de meta si entra en el tramo visible.
        y_meta = int(Y_JUGADOR - (META - jugador.distancia) * ESCALA_M)
        if -35 < y_meta < ALTO:
            for xx in range(145, 656, 22):
                color = BLANCO if (xx // 22) % 2 == 0 else NEGRO
                pygame.draw.rect(pantalla, color, (xx, y_meta, 22, 15))
            dibujar_texto("META", 400, y_meta-18, AMARILLO, fuente_mediana, centro=True)

        brecha = jugador.distancia - cpu.distancia
        if brecha > 35:
            posicion = "VAS GANANDO"
            color_pos = VERDE_NEON
        elif brecha < -35:
            posicion = "EL COMPUTADOR VA GANANDO"
            color_pos = ROJO_CLARO
        else:
            posicion = "¡CARRERA MUY PAREJA!"
            color_pos = AMARILLO
        if estado_app == "jugando":
            dibujar_hud(jugador, cpu, posicion)
        else:
            dibujar_hud(jugador, cpu)

        # Barra de nitro abajo.
        panel((18, 715, 265, 63), (18, 28, 42), (54, 72, 94), 13, 1)
        dibujar_texto("NITRO  ·  SHIFT", 31, 724, AZUL_CLARO, fuente_chica)
        pygame.draw.rect(pantalla, (48, 59, 75), (31, 749, 235, 13), border_radius=6)
        if jugador.nitro > 0:
            pygame.draw.rect(pantalla, AZUL, (31, 749, int(235*jugador.nitro/100), 13), border_radius=6)
        dibujar_texto("M: sonido ON" if SONIDO_ACTIVO else "M: sonido OFF", 778, 749, BLANCO, fuente_chica, centro=True)

        if estado_app == "cuenta":
            capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            capa.fill((5, 9, 15, 70))
            pantalla.blit(capa, (0, 0))
            num = max(1, math.ceil(carrera["cuenta_atras"]))
            titulo = "¡YA!" if carrera["cuenta_atras"] < 0.7 else str(num)
            dibujar_texto(titulo, 400, 400, AMARILLO, fuente_logo, centro=True)
        elif estado_app == "pausa":
            dibujar_pausa()
        elif estado_app == "resultado":
            dibujar_resultado(carrera["ganador"], jugador, cpu)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
