# Ajedrez en Python 3.13 (VS Code)

Juego gráfico de ajedrez para una persona contra una computadora sencilla.

## Funciones
- Tablero gráfico y selección/movimiento con el mouse.
- Movimientos legales, jaque, jaque mate y tablas.
- Enroque, captura al paso (en passant) y promoción a reina, torre, alfil o caballo.
- Computadora con búsqueda minimax y poda alpha-beta (nivel básico/intermedio).
- Botones para nueva partida y deshacer turno.

## Requisitos
- Windows 10/11
- Python 3.13
- VS Code con la extensión Python

## Instalación
Abre una terminal en esta carpeta y ejecuta:

```powershell
py -3.13 -m pip install -r requirements.txt
```

Si `py -3.13` no funciona, selecciona el intérprete Python 3.13 en VS Code y usa:

```powershell
python -m pip install -r requirements.txt
```

## Ejecutar

```powershell
py -3.13 ajedrez.py
```

O, con el intérprete seleccionado:

```powershell
python ajedrez.py
```

## Cómo jugar
- Tú juegas con las blancas y empiezas.
- Haz clic en una pieza blanca: las casillas legales se marcan.
- Haz clic en el destino para mover.
- Cuando un peón llegue al final, elige la pieza de promoción.
- `R`: nueva partida.
- `Esc`: cancelar selección.
- Usa **Deshacer turno** para retirar tu última jugada y la respuesta de la computadora.
- Cierra la ventana para salir.

## Notas
La lógica de reglas se basa en la biblioteca `python-chess`. La computadora es una IA de búsqueda sencilla; no es un motor profesional como Stockfish.
