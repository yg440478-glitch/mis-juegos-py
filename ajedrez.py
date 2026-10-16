import sys
import pygame
import chess
import chess.engine

# Ajedrez grafico: jugador con blancas contra una computadora sencilla.
# Reglas completas gestionadas por python-chess: movimientos legales,
# jaque, jaque mate, enroque, en passant, tablas y promocion.

pygame.init()
ANCHO, ALTO = 800, 800
TAM_CASILLA = 80
TABLERO_X, TABLERO_Y = 40, 40
PANEL_Y = TABLERO_Y + 8 * TAM_CASILLA

pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Ajedrez - Jugador vs Computadora")
reloj = pygame.time.Clock()

CREMA = (238, 238, 210)
VERDE = (118, 150, 86)
VERDE_OSCURO = (65, 95, 55)
AMARILLO = (245, 230, 90)
ROJO = (210, 65, 65)
FONDO = (30, 34, 40)
BLANCO = (250, 250, 245)
NEGRO = (25, 25, 28)
GRIS = (190, 195, 200)
AZUL = (75, 145, 220)

fuente_estado = pygame.font.SysFont("arial", 22)
fuente_pequena = pygame.font.SysFont("arial", 17)
fuente_pieza = pygame.font.SysFont("segoeuisymbol", 58)
fuente_boton = pygame.font.SysFont("arial", 18, bold=True)

# Simbolos Unicode de ajedrez; se usa una fuente instalada en Windows.
SIMBOLOS = {
    (chess.WHITE, chess.KING): "♔", (chess.WHITE, chess.QUEEN): "♕",
    (chess.WHITE, chess.ROOK): "♖", (chess.WHITE, chess.BISHOP): "♗",
    (chess.WHITE, chess.KNIGHT): "♘", (chess.WHITE, chess.PAWN): "♙",
    (chess.BLACK, chess.KING): "♚", (chess.BLACK, chess.QUEEN): "♛",
    (chess.BLACK, chess.ROOK): "♜", (chess.BLACK, chess.BISHOP): "♝",
    (chess.BLACK, chess.KNIGHT): "♞", (chess.BLACK, chess.PAWN): "♟",
}

tablero = chess.Board()
seleccion = None
movimientos_seleccion = []
mensaje = "Tu turno: juega con las blancas."
pensando = False
fin = False
promocion_pendiente = None

BOTONES = {
    "reiniciar": pygame.Rect(40, 690, 130, 25),
}
# La ventana se mantiene en 800x720; los botones se dibujan dentro del panel.
BOTON_REINICIAR = pygame.Rect(600, 735, 155, 38)
BOTON_DESHACER = pygame.Rect(430, 735, 155, 38)

def texto(superficie, contenido, fuente, color, pos, centrado=False):
    imagen = fuente.render(contenido, True, color)
    rect = imagen.get_rect()
    if centrado:
        rect.center = pos
    else:
        rect.topleft = pos
    superficie.blit(imagen, rect)

def casilla_a_pixel(casilla):
    col = chess.square_file(casilla)
    fila = 7 - chess.square_rank(casilla)
    return TABLERO_X + col * TAM_CASILLA, TABLERO_Y + fila * TAM_CASILLA

def pixel_a_casilla(pos):
    x, y = pos
    if not (TABLERO_X <= x < TABLERO_X + 8*TAM_CASILLA and
            TABLERO_Y <= y < TABLERO_Y + 8*TAM_CASILLA):
        return None
    col = (x - TABLERO_X) // TAM_CASILLA
    fila_visual = (y - TABLERO_Y) // TAM_CASILLA
    return chess.square(col, 7 - fila_visual)

def estado_partida():
    if tablero.is_checkmate():
        ganador = "Negras" if tablero.turn == chess.WHITE else "Blancas"
        return f"JAQUE MATE: ganan {ganador}."
    if tablero.is_stalemate():
        return "Tablas por ahogado."
    if tablero.is_insufficient_material():
        return "Tablas: material insuficiente."
    if tablero.is_seventyfive_moves():
        return "Tablas por regla de 75 movimientos."
    if tablero.is_fivefold_repetition():
        return "Tablas por repeticion."
    if tablero.is_check():
        return "JAQUE. " + ("Tu turno." if tablero.turn else "Turno de la computadora.")
    return "Tu turno: juega con las blancas." if tablero.turn == chess.WHITE else "Turno de la computadora..."

def dibujar_tablero():
    for fila in range(8):
        for col in range(8):
            sq = chess.square(col, 7 - fila)
            rect = pygame.Rect(TABLERO_X + col*TAM_CASILLA,
                               TABLERO_Y + fila*TAM_CASILLA,
                               TAM_CASILLA, TAM_CASILLA)
            color = CREMA if (fila + col) % 2 == 0 else VERDE
            pygame.draw.rect(pantalla, color, rect)

            if seleccion == sq:
                pygame.draw.rect(pantalla, AMARILLO, rect, 5)

            if tablero.move_stack:
                ultimo = tablero.peek()
                if sq in (ultimo.from_square, ultimo.to_square):
                    pygame.draw.rect(pantalla, (230, 190, 65), rect, 4)

            pieza = tablero.piece_at(sq)
            if pieza:
                simbolo = SIMBOLOS[(pieza.color, pieza.piece_type)]
                color_pieza = BLANCO if pieza.color == chess.WHITE else NEGRO
                sombra = (25, 25, 25) if pieza.color == chess.WHITE else (240, 240, 235)
                superficie = fuente_pieza.render(simbolo, True, sombra)
                rect_texto = superficie.get_rect(center=rect.center)
                pantalla.blit(superficie, rect_texto)
                # Un borde sutil ayuda a distinguir las piezas.
                if pieza.color == chess.WHITE:
                    pygame.draw.circle(pantalla, (210, 210, 195), rect.center, 25, 1)

    for movimiento in movimientos_seleccion:
        x, y = casilla_a_pixel(movimiento.to_square)
        centro = (x + TAM_CASILLA//2, y + TAM_CASILLA//2)
        if tablero.piece_at(movimiento.to_square):
            pygame.draw.circle(pantalla, ROJO, centro, 32, 4)
        else:
            pygame.draw.circle(pantalla, VERDE_OSCURO, centro, 9)

    # Coordenadas del tablero.
    for col in range(8):
        letra = chr(ord("a") + col)
        texto(pantalla, letra, fuente_pequena, BLANCO,
              (TABLERO_X + col*TAM_CASILLA + 5, TABLERO_Y + 8*TAM_CASILLA - 20))
    for fila in range(8):
        numero = str(8 - fila)
        texto(pantalla, numero, fuente_pequena, BLANCO,
              (TABLERO_X + 3, TABLERO_Y + fila*TAM_CASILLA + 3))

def elegir_promocion(movimientos):
    # Ventana simple de opciones: Reina, torre, alfil o caballo.
    opciones = [
        (chess.QUEEN, "Reina"),
        (chess.ROOK, "Torre"),
        (chess.BISHOP, "Alfil"),
        (chess.KNIGHT, "Caballo"),
    ]
    overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    pantalla.blit(overlay, (0, 0))
    caja = pygame.Rect(120, 280, 560, 150)
    pygame.draw.rect(pantalla, BLANCO, caja, border_radius=12)
    texto(pantalla, "Elige la pieza para promocionar", fuente_estado, NEGRO,
          (ANCHO//2, 305), centrado=True)
    rects = []
    for i, (tipo, nombre) in enumerate(opciones):
        rect = pygame.Rect(140 + i*130, 340, 120, 65)
        pygame.draw.rect(pantalla, AZUL, rect, border_radius=8)
        texto(pantalla, nombre, fuente_pequena, BLANCO, rect.center, centrado=True)
        rects.append((rect, tipo))
    pygame.display.flip()
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
                return chess.QUEEN
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for rect, tipo in rects:
                    if rect.collidepoint(evento.pos):
                        return tipo
        reloj.tick(30)

def movimiento_computadora():
    # Evaluacion minimax sencilla con poda alpha-beta. La computadora juega
    # legalmente y busca capturas, jaques y posiciones favorables.
    valores = {
        chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
        chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 20000,
    }

    def evaluar(board):
        if board.is_checkmate():
            return -100000 if board.turn == chess.WHITE else 100000
        puntuacion = 0
        for sq, pieza in board.piece_map().items():
            valor = valores[pieza.piece_type]
            fila, col = chess.square_rank(sq), chess.square_file(sq)
            # Ligero incentivo por controlar el centro y avanzar peones.
            centralidad = 3 - abs(3.5-col) - abs(3.5-fila)
            extra = int(centralidad * 5)
            if pieza.piece_type == chess.PAWN:
                extra += (fila * 7) if pieza.color == chess.WHITE else ((7-fila) * 7)
            puntuacion += (valor + extra) * (1 if pieza.color == chess.WHITE else -1)
        return puntuacion

    def minimax(board, profundidad, alfa, beta, maximizando):
        if profundidad == 0 or board.is_game_over(claim_draw=True):
            return evaluar(board), None
        mejor_mov = None
        if maximizando:
            mejor = -float("inf")
            for mov in orden_movimientos(board):
                board.push(mov)
                valor, _ = minimax(board, profundidad-1, alfa, beta, False)
                board.pop()
                if valor > mejor:
                    mejor, mejor_mov = valor, mov
                alfa = max(alfa, mejor)
                if beta <= alfa:
                    break
            return mejor, mejor_mov
        mejor = float("inf")
        for mov in orden_movimientos(board):
            board.push(mov)
            valor, _ = minimax(board, profundidad-1, alfa, beta, True)
            board.pop()
            if valor < mejor:
                mejor, mejor_mov = valor, mov
            beta = min(beta, mejor)
            if beta <= alfa:
                break
        return mejor, mejor_mov

    def orden_movimientos(board):
        movimientos = list(board.legal_moves)
        movimientos.sort(key=lambda m: (
            board.is_capture(m),
            m.promotion is not None,
            board.gives_check(m)
        ), reverse=True)
        return movimientos

    # Las negras minimizan la puntuacion desde la perspectiva de blancas.
    _, mejor = minimax(tablero, 2, -float("inf"), float("inf"), False)
    if mejor is None:
        legales = list(tablero.legal_moves)
        return random.choice(legales) if legales else None
    return mejor

def dibujar():
    pantalla.fill(FONDO)
    dibujar_tablero()

    pygame.draw.rect(pantalla, (42, 47, 55), (0, 680, ANCHO, 120))
    texto(pantalla, f"Turno: {'Blancas (tu)' if tablero.turn == chess.WHITE else 'Negras (IA)'}",
          fuente_estado, BLANCO, (40, 690))
    texto(pantalla, mensaje, fuente_pequena, GRIS, (40, 720))

    pygame.draw.rect(pantalla, AZUL, BOTON_DESHACER, border_radius=7)
    texto(pantalla, "Deshacer turno", fuente_boton, BLANCO,
          BOTON_DESHACER.center, centrado=True)
    pygame.draw.rect(pantalla, ROJO, BOTON_REINICIAR, border_radius=7)
    texto(pantalla, "Nueva partida", fuente_boton, BLANCO,
          BOTON_REINICIAR.center, centrado=True)

    if tablero.is_check():
        rey = tablero.king(tablero.turn)
        if rey is not None:
            x, y = casilla_a_pixel(rey)
            pygame.draw.rect(pantalla, ROJO,
                             (x, y, TAM_CASILLA, TAM_CASILLA), 5)

    pygame.display.flip()

def deshacer_turno():
    # Deshace la jugada de la IA y la jugada del usuario, si existen.
    if tablero.move_stack:
        tablero.pop()
    if tablero.move_stack and tablero.turn == chess.BLACK:
        tablero.pop()

while True:
    dibujar()
    if tablero.is_game_over(claim_draw=True):
        mensaje = estado_partida()
        dibujar()
        esperando = True
        while esperando:
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                    if BOTON_REINICIAR.collidepoint(evento.pos):
                        tablero.reset()
                        seleccion = None
                        movimientos_seleccion = []
                        mensaje = "Nueva partida. Tu turno."
                        esperando = False
            reloj.tick(30)
        continue

    if tablero.turn == chess.BLACK:
        pygame.event.pump()
        mensaje = "La computadora esta pensando..."
        dibujar()
        mov = movimiento_computadora()
        if mov is not None:
            tablero.push(mov)
        seleccion = None
        movimientos_seleccion = []
        mensaje = estado_partida()
        continue

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                seleccion = None
                movimientos_seleccion = []
            elif evento.key == pygame.K_r:
                tablero.reset()
                seleccion = None
                movimientos_seleccion = []
                mensaje = "Nueva partida. Tu turno."

        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            if BOTON_REINICIAR.collidepoint(evento.pos):
                tablero.reset()
                seleccion = None
                movimientos_seleccion = []
                mensaje = "Nueva partida. Tu turno."
                continue

            if BOTON_DESHACER.collidepoint(evento.pos):
                deshacer_turno()
                seleccion = None
                movimientos_seleccion = []
                mensaje = estado_partida()
                continue

            casilla = pixel_a_casilla(evento.pos)
            if casilla is None:
                continue

            pieza = tablero.piece_at(casilla)
            if seleccion is None:
                if pieza and pieza.color == chess.WHITE:
                    seleccion = casilla
                    movimientos_seleccion = [
                        m for m in tablero.legal_moves if m.from_square == seleccion
                    ]
                else:
                    mensaje = "Selecciona una pieza blanca."
            else:
                candidatos = [
                    m for m in movimientos_seleccion if m.to_square == casilla
                ]
                if candidatos:
                    mov = candidatos[0]
                    if mov.promotion:
                        tipo = elegir_promocion(candidatos)
                        mov = chess.Move(mov.from_square, mov.to_square, promotion=tipo)
                    tablero.push(mov)
                    seleccion = None
                    movimientos_seleccion = []
                    mensaje = estado_partida()
                elif pieza and pieza.color == chess.WHITE:
                    seleccion = casilla
                    movimientos_seleccion = [
                        m for m in tablero.legal_moves if m.from_square == seleccion
                    ]
                else:
                    seleccion = None
                    movimientos_seleccion = []

    reloj.tick(60)
