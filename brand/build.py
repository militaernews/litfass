"""Builds the litfass logo and social image in the Militär-News radar look: python build.py (needs resvg-py)."""
import math
from pathlib import Path

HERE = Path(__file__).parent

# Geometric stroke letters, 100 units high, like the Militär-News wordmark (A without crossbar)
GLYPHS = {
    "L": ("M0 0V100H56", 56),
    "I": ("M0 0V100", 0),
    "T": ("M0 0H62M31 0V100", 62),
    "F": ("M0 100V0H56M0 48H44", 56),
    "A": ("M0 100L31 0L62 100", 62),
    "S": ("M60 0H10Q0 0 0 10V40Q0 50 10 50H50Q60 50 60 60V90Q60 100 50 100H0", 60),
}


def wordmark(text: str, x: float, y: float, height: float, gap: float = 26) -> str:
    scale = height / 100
    parts, cursor = [], 0.0
    for char in text:
        path, width = GLYPHS[char]
        parts.append(f'<path transform="translate({cursor:.1f} 0)" d="{path}"/>')
        cursor += width + gap
    return (
        f'<g transform="translate({x} {y}) scale({scale})" fill="none" stroke="#f2fbff" stroke-width="9" '
        f'stroke-linecap="square" stroke-linejoin="miter" filter="url(#glow)">{"".join(parts)}</g>'
    )


def radar(cx: float, cy: float, r: float) -> str:
    rings = "".join(f'<circle cx="{cx}" cy="{cy}" r="{r * f:.1f}" fill="none" stroke="#5fd0ff" stroke-opacity=".28" stroke-width="2"/>' for f in (0.25, 0.5, 0.75))
    spokes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{cx + r * math.cos(math.radians(a)):.1f}" y2="{cy + r * math.sin(math.radians(a)):.1f}" stroke="#5fd0ff" stroke-opacity="{0.3 if a % 90 == 0 else 0.13}" stroke-width="{2 if a % 90 == 0 else 1.5}"/>'
        for a in range(0, 360, 30)
    )
    ticks = f'<circle cx="{cx}" cy="{cy}" r="{r - 9:.1f}" fill="none" stroke="#7fdcff" stroke-opacity=".45" stroke-width="6" stroke-dasharray="1.5 {2 * math.pi * (r - 9) / 120 - 1.5:.2f}"/>'
    # The sweep: a wedge fading out behind the beam
    a0, a1 = math.radians(-100), math.radians(-40)
    sweep = (
        f'<path d="M{cx} {cy}L{cx + r * math.cos(a0):.1f} {cy + r * math.sin(a0):.1f}A{r} {r} 0 0 1 {cx + r * math.cos(a1):.1f} {cy + r * math.sin(a1):.1f}Z" fill="url(#sweep)"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{cx + r * math.cos(a1):.1f}" y2="{cy + r * math.sin(a1):.1f}" stroke="#9be7ff" stroke-opacity=".8" stroke-width="2.5"/>'
    )
    blips = "".join(
        f'<circle cx="{cx + r * d * math.cos(math.radians(a)):.1f}" cy="{cy + r * d * math.sin(math.radians(a)):.1f}" r="{s}" fill="#8fe6ff" filter="url(#glow)"/>'
        for a, d, s in ((-60, 0.62, 5), (-75, 0.35, 3.5), (200, 0.7, 4), (150, 0.55, 3), (30, 0.8, 4.5), (100, 0.82, 3), (-20, 0.45, 3))
    )
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#screen)"/>{rings}{spokes}{sweep}{blips}{ticks}'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2ec5ff" stroke-opacity=".7" stroke-width="3"/>'
    )


DEFS = """<defs>
	<radialGradient id="screen" cx=".45" cy=".4" r=".7">
		<stop offset="0" stop-color="#1f6fae"/><stop offset=".55" stop-color="#0c3a6b"/><stop offset="1" stop-color="#061a36"/>
	</radialGradient>
	<linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
		<stop offset="0" stop-color="#2ec5ff" stop-opacity="0"/><stop offset="1" stop-color="#2ec5ff" stop-opacity=".35"/>
	</linearGradient>
	<linearGradient id="col" x1="0" x2="1">
		<stop offset="0" stop-color="#04122a" stop-opacity=".95"/><stop offset=".5" stop-color="#0d3768" stop-opacity=".9"/><stop offset="1" stop-color="#04122a" stop-opacity=".95"/>
	</linearGradient>
	<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
		<feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
	</filter>
	<clipPath id="column"><rect x="178" y="156" width="156" height="260"/></clipPath>
</defs>"""

# The advertising pillar as glowing line art; posters are lit panels in the radar's blues
PILLAR = """<g>
	<rect x="176" y="150" width="160" height="270" fill="url(#col)"/>
	<g clip-path="url(#column)">
		<rect x="186" y="172" width="66" height="96" rx="3" fill="#2ec5ff" fill-opacity=".85"/>
		<rect x="196" y="186" width="44" height="8" rx="2" fill="#f2fbff"/>
		<rect x="196" y="200" width="32" height="6" rx="2" fill="#f2fbff" fill-opacity=".8"/>
		<path d="M219 220l6 13 14 2-10 10 2 14-12-7-12 7 2-14-10-10 14-2z" fill="#f2fbff"/>
		<rect x="260" y="172" width="66" height="62" rx="3" fill="#f2fbff" fill-opacity=".92"/>
		<rect x="270" y="184" width="40" height="8" rx="2" fill="#0c3a6b"/>
		<rect x="270" y="198" width="46" height="5" rx="2" fill="#0c3a6b" fill-opacity=".7"/>
		<rect x="270" y="209" width="32" height="5" rx="2" fill="#0c3a6b" fill-opacity=".7"/>
		<rect x="260" y="242" width="66" height="92" rx="3" fill="#1f6fae"/>
		<circle cx="293" cy="278" r="18" fill="none" stroke="#9be7ff" stroke-width="3"/>
		<path d="M287 268L302 278L287 288Z" fill="#9be7ff"/>
		<rect x="272" y="310" width="42" height="6" rx="2" fill="#9be7ff"/>
		<rect x="186" y="276" width="66" height="58" rx="3" fill="#0f4c81"/>
		<rect x="196" y="288" width="44" height="9" rx="2" fill="#2ec5ff"/>
		<rect x="196" y="304" width="48" height="5" rx="2" fill="#f2fbff" fill-opacity=".7"/>
		<rect x="196" y="315" width="36" height="5" rx="2" fill="#f2fbff" fill-opacity=".7"/>
		<rect x="186" y="342" width="140" height="58" rx="3" fill="#9be7ff" fill-opacity=".9"/>
		<rect x="198" y="358" width="80" height="9" rx="2" fill="#061a36"/>
		<rect x="198" y="374" width="56" height="6" rx="2" fill="#061a36" fill-opacity=".7"/>
		<rect x="288" y="356" width="28" height="28" rx="4" fill="#061a36"/>
	</g>
	<g fill="none" stroke="#bdefff" stroke-width="4" filter="url(#glow)">
		<rect x="176" y="150" width="160" height="270"/>
		<path d="M170 140Q170 74 256 66Q342 74 342 140"/>
		<rect x="160" y="136" width="192" height="16" rx="4"/>
		<rect x="166" y="420" width="180" height="18" rx="3"/>
		<path d="M256 66V50"/>
	</g>
	<path d="M170 140Q170 74 256 66Q342 74 342 140Z" fill="#082a52" fill-opacity=".85"/>
	<path d="M200 128Q206 92 256 84" fill="none" stroke="#9be7ff" stroke-opacity=".45" stroke-width="5" stroke-linecap="round"/>
	<circle cx="256" cy="44" r="9" fill="#9be7ff" filter="url(#glow)"/>
</g>"""


def svg(width: int, height: int, body: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">{DEFS}{body}</svg>'


logo = svg(512, 512, f'<rect width="512" height="512" fill="#1b1029"/>{radar(256, 256, 240)}{PILLAR}')
social = svg(
    1280,
    640,
    '<rect width="1280" height="640" fill="#1b1029"/>'
    f"{radar(320, 320, 290)}"
    f'<g transform="translate(320 320) scale(1.12) translate(-256 -248)">{PILLAR}</g>'
    + wordmark("LITFASS", 660, 205, 96, gap=22)
    + '<text x="662" y="400" font-family="Noto Sans" font-size="36" fill="#cfefff">House adverts for web games,</text>'
    '<text x="662" y="446" font-family="Noto Sans" font-size="36" fill="#cfefff">Mini Apps and Telegram bots.</text>'
    '<text x="662" y="512" font-family="Noto Sans" font-weight="700" font-size="22" fill="#2ec5ff" letter-spacing="1">NO AD NETWORK · NO TRACKING · ONE JSON FEED</text>',
)

(HERE / "logo.svg").write_text(logo)
(HERE / "social.svg").write_text(social)

try:
    import resvg_py

    fonts = [str(p) for p in Path.home().glob(".local/share/fonts/truetype/noto/NotoSans-*.ttf")]
    for name, width in (("logo", 640), ("social", 1280)):
        png = resvg_py.svg_to_bytes(svg_path=str(HERE / f"{name}.svg"), width=width, font_files=fonts or None)
        (HERE / f"{name}.png").write_bytes(bytes(png))
except ImportError:
    print("resvg-py not installed: SVGs written, PNGs unchanged")
