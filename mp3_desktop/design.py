"""Design system do Media Studio.

Paleta oficial verde-azulada (petróleo/turquesa) com tokens semânticos.
Uma fonte única de cores, tipografia, espaçamento, raios e bordas.
"""

from __future__ import annotations

# ————————————————————————————— Paleta oficial —————————————————————————————
# Tokens base da marca Media Studio.
PALETTE = {
    "bg": "#04222B",  # Background principal
    "surface": "#0A3D4A",  # Superfície secundária
    "surface_elevated": "#10606F",  # Superfície elevada
    "petroleo": "#1D8B94",  # Azul-petróleo
    "turquesa": "#4FB8B4",  # Turquesa principal
    "turquesa_claro": "#98D8D0",  # Turquesa claro
    "branco_suave": "#E2F4F0",  # Branco suave
}

# Tokens semânticos para tema escuro (único tema suportado)
DARK = {
    # Cores de fundo e superfície
    "bg": PALETTE["bg"],
    "surface": PALETTE["surface"],
    "surface_hover": "#0E4B5B",
    "surface_elevated": PALETTE["surface_elevated"],
    "border": "#1F5C63",
    "border_focus": PALETTE["turquesa"],
    "border_input": "#2A6B72",
    # Texto
    "text_primary": PALETTE["branco_suave"],
    "text_secondary": PALETTE["turquesa_claro"],
    "text_muted": "#6E9E9A",
    "text_inverse": PALETTE["bg"],
    # Ação / destaque
    "primary": PALETTE["turquesa"],
    "primary_hover": "#6FC8C6",
    "primary_active": "#3FA09E",
    "primary_light": "rgba(79, 184, 180, 0.15)",
    "ink": PALETTE["branco_suave"],
    # Estados semânticos
    "success": "#4FB8B4",
    "success_bg": "rgba(79, 184, 180, 0.10)",
    "warning": "#98D8D0",
    "warning_bg": "rgba(152, 216, 208, 0.10)",
    "error": "#FF6B6B",
    "error_bg": "rgba(255, 107, 107, 0.10)",
    "info": "#1D8B94",
    "info_bg": "rgba(29, 139, 148, 0.10)",
    # Estados de interação
    "hover": "rgba(79, 184, 180, 0.08)",
    "active": "rgba(79, 184, 180, 0.15)",
    "disabled": "rgba(152, 216, 208, 0.30)",
    "disabled_text": "rgba(152, 216, 208, 0.45)",
    "focus_ring": "0 0 0 3px rgba(79, 184, 180, 0.35)",
    # Barra de progresso
    "progress_track": "#1F5C63",
    "progress_fill": PALETTE["turquesa"],
    # Sombra sutil (sem cor exagerada)
    "shadow": "0 1px 3px rgba(0, 0, 0, 0.30)",
}

# Estados (feedback sem competir com o primary)
ERROR = "#FF6B6B"
ERROR_BG = "rgba(255, 107, 107, 0.10)"
SUCCESS = "#4FB8B4"
SUCCESS_BG = "rgba(79, 184, 180, 0.10)"
WARNING = "#98D8D0"
WARNING_BG = "rgba(152, 216, 208, 0.10)"

# ————————————————————————————— Espaçamento (escala 4px) —————————————————————————————
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 20
SPACE_6 = 24
SPACE_8 = 32
SPACE_10 = 40

# ————————————————————————————— Raios e bordas —————————————————————————————
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14
RADIUS_XL = 20
BORDER_WIDTH = 1
BORDER_WIDTH_INPUT = 1

# ————————————————————————————— Tipografia —————————————————————————————
FONT = "Segoe UI"
FONT_SEMIBOLD = "Segoe UI Semibold"
FONT_MONO = "Consolas"

TEXT_SIZE_CAPTION = 11
TEXT_SIZE_SMALL = 12
TEXT_SIZE_BASE = 14
TEXT_SIZE_MEDIUM = 16
TEXT_SIZE_LARGE = 18
TEXT_SIZE_SECTION = 13
TEXT_SIZE_TITLE = 24
TEXT_SIZE_DISPLAY = 32

FONT_WEIGHT_REGULAR = 400
FONT_WEIGHT_MEDIUM = 500
FONT_WEIGHT_SEMIBOLD = 600
FONT_WEIGHT_BOLD = 700

LINE_HEIGHT_TIGHT = 1.25
LINE_HEIGHT_NORMAL = 1.5
LINE_HEIGHT_RELAXED = 1.6

# ————————————————————————————— Z-index —————————————————————————————
Z_DROPDOWN = 100
Z_MODAL = 200
Z_TOAST = 300
Z_TOOLTIP = 400

# ————————————————————————————— Helpers —————————————————————————————


def colors(dark: bool = True) -> dict:
    return DARK
