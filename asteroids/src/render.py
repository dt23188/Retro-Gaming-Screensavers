"""Sleek, asset-free Cairo vector art over true black."""

import math
import random
from functools import lru_cache
import cairo
from engine import Vec, Ship, FLEET_COLORS, WARP_DURATION


def path(cr, points, close=True):
    cr.move_to(*points[0])
    for point in points[1:]:
        cr.line_to(*point)
    if close:
        cr.close_path()


def glow(cr, x, y, radius, color, strength=0.3):
    gradient = cairo.RadialGradient(x, y, 0, x, y, radius)
    gradient.add_color_stop_rgba(0, *color, strength)
    gradient.add_color_stop_rgba(1, *color, 0)
    cr.set_source(gradient)
    cr.arc(x, y, radius, 0, math.tau)
    cr.fill()


@lru_cache(maxsize=384)
def rock_surface(radius, outline):
    """Cache stable rock textures so craters never flicker between frames."""
    seed = sum(int(value * 1_000_000) * (i + 31) for i, value in enumerate(outline))
    rng = random.Random(seed)
    palettes = [
        (0.54, 0.43, 0.33),
        (0.43, 0.48, 0.53),
        (0.52, 0.38, 0.30),
        (0.40, 0.46, 0.40),
    ]
    base = palettes[rng.randrange(len(palettes))]
    size = math.ceil(radius * 2.3) + 16
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    cr = cairo.Context(surface)
    cr.translate(size / 2, size / 2)
    points = [
        (
            math.cos(i * math.tau / len(outline)) * r * radius,
            math.sin(i * math.tau / len(outline)) * r * radius,
        )
        for i, r in enumerate(outline)
    ]
    path(cr, points)
    shade = cairo.RadialGradient(-radius * 0.40, -radius * 0.45, 0, 0, 0, radius * 1.2)
    shade.add_color_stop_rgb(0, *(min(1, c * 1.35) for c in base))
    shade.add_color_stop_rgb(0.48, *base)
    shade.add_color_stop_rgb(1, *(c * 0.22 for c in base))
    cr.set_source(shade)
    cr.fill_preserve()
    cr.save()
    cr.clip()
    # Broken angular planes give a rough silhouette and mineral facets.
    center = (rng.uniform(-0.2, 0.2) * radius, rng.uniform(-0.2, 0.2) * radius)
    for i in range(len(points)):
        path(cr, [center, points[i], points[(i + 1) % len(points)]])
        brightness = rng.uniform(0.05, 0.15)
        if i % 3:
            cr.set_source_rgba(0.85, 0.82, 0.72, brightness)
        else:
            cr.set_source_rgba(0.02, 0.03, 0.04, brightness * 1.8)
        cr.fill()
    for _ in range(int(radius * 1.4)):
        x, y = rng.uniform(-radius, radius), rng.uniform(-radius, radius)
        cr.set_source_rgba(0.08, 0.07, 0.06, rng.uniform(0.12, 0.30))
        cr.arc(x, y, rng.uniform(0.3, 1.2), 0, math.tau)
        cr.fill()
    # Recessed bowls, shaded walls, raised sunlit lips, and small impact pits.
    craters = []
    for _ in range(60):
        if len(craters) >= (6 if radius > 40 else 4 if radius > 25 else 2):
            break
        x, y = rng.uniform(-0.55, 0.55) * radius, rng.uniform(-0.55, 0.55) * radius
        r = rng.uniform(0.10, 0.23) * radius
        if any(math.hypot(x - px, y - py) < r + pr + 2 for px, py, pr in craters):
            continue
        craters.append((x, y, r))
        cr.save()
        cr.translate(x, y)
        cr.scale(1, rng.uniform(0.72, 0.96))
        bowl = cairo.RadialGradient(r * 0.35, r * 0.40, 0, 0, 0, r)
        bowl.add_color_stop_rgb(0, *(c * 0.65 for c in base))
        bowl.add_color_stop_rgb(0.58, *(c * 0.30 for c in base))
        bowl.add_color_stop_rgb(1, *(c * 0.12 for c in base))
        cr.set_source(bowl)
        cr.arc(0, 0, r, 0, math.tau)
        cr.fill()
        cr.set_line_width(max(0.8, r * 0.15))
        cr.set_source_rgba(0.03, 0.025, 0.02, 0.80)
        cr.arc(0, 0, r * 1.05, math.pi * 0.95, math.pi * 1.95)
        cr.stroke()
        cr.set_source_rgba(*(min(1, c * 1.6) for c in base), 0.78)
        cr.arc(0, 0, r * 1.03, 0, math.pi * 0.85)
        cr.stroke()
        cr.set_line_width(0.6)
        cr.set_source_rgba(0.80, 0.76, 0.65, 0.24)
        cr.arc(r * 0.15, r * 0.2, r * 0.63, 0, math.pi * 0.8)
        cr.stroke()
        cr.restore()
    # Thin fissures tie the craters and uneven planes together.
    for i in range(3):
        start = points[(i * 3 + 1) % len(points)]
        path(
            cr,
            [
                start,
                (start[0] * 0.5 + 3, start[1] * 0.4),
                (start[0] * 0.15, start[1] * 0.2 + 5),
            ],
            False,
        )
        cr.set_source_rgba(0.04, 0.035, 0.03, 0.40)
        cr.set_line_width(0.8)
        cr.stroke()
    cr.restore()
    path(cr, points)
    rim = cairo.LinearGradient(-radius, -radius, radius, radius)
    rim.add_color_stop_rgba(0, 0.85, 0.81, 0.70, 0.78)
    rim.add_color_stop_rgba(0.45, *base, 0.7)
    rim.add_color_stop_rgba(1, 0.06, 0.07, 0.08, 0.85)
    cr.set_source(rim)
    cr.set_line_width(1.4)
    cr.stroke()
    return surface


def draw_shield(cr, now):
    """A transparent blue-violet energy sphere with a luminous curved rim."""
    pulse = .5 + .5 * math.sin(now * 2.4)
    radius = 35 + pulse * 1.2
    glow(cr, 0, 0, radius * 1.6, (.30, .24, 1), .18 + pulse * .04)
    sphere = cairo.RadialGradient(-radius * .18, -radius * .22, 0,
                                  0, 0, radius)
    sphere.add_color_stop_rgba(0, .48, .72, 1, .025)
    sphere.add_color_stop_rgba(.50, .25, .48, 1, .055)
    sphere.add_color_stop_rgba(.78, .35, .25, 1, .14)
    sphere.add_color_stop_rgba(.94, .56, .30, 1, .34)
    sphere.add_color_stop_rgba(1, .34, .65, 1, .58)
    cr.set_source(sphere)
    cr.arc(0, 0, radius, 0, math.tau)
    cr.fill()
    rim = cairo.LinearGradient(-radius, -radius, radius, radius)
    rim.add_color_stop_rgba(0, .65, .88, 1, .85)
    rim.add_color_stop_rgba(.45, .24, .50, 1, .36)
    rim.add_color_stop_rgba(1, .72, .35, 1, .72)
    cr.set_source(rim)
    cr.set_line_width(1.3)
    cr.arc(0, 0, radius, 0, math.tau)
    cr.stroke()
    # A soft specular reflection makes the field read as an orb, not a ring.
    glow(cr, -radius * .42, -radius * .65, radius * .28, (.65, .86, 1), .34)


def muzzle_flash(cr, remaining, color, nose=23):
    if remaining <= 0:
        return
    fade = min(1, remaining / .09)
    # Light washes back over the forward hull and blooms at the muzzle.
    glow(cr, nose - 5, 0, 28, color, .65 * fade)
    path(cr, [(nose, 0), (nose - 21, -8), (nose - 21, 8)])
    cr.set_source_rgba(*color, .45 * fade)
    cr.fill()
    glow(cr, nose + 4, 0, 17, color, .75 * fade)
    path(cr, [(nose - 2, -2), (nose + 15 * fade, 0), (nose - 2, 2)])
    cr.set_source_rgba(1, 1, .9, fade)
    cr.fill()


def draw_ship(cr, ship, now):
    """Metal-plated delta hull, blue glass canopy, and twin engine nacelles."""
    if ship.thrust:
        pulse = 0.5 + 0.5 * math.sin(now * 27)
        for side in [-1, 1]:
            y = side * 10.5
            length = 25 + pulse * 15 + math.sin(now * 73 + side) * 4
            glow(cr, -24, y, 30 + pulse * 6, (0.16, 0.60, 1), 0.27)
            plume = cairo.LinearGradient(-21, y, -21 - length, y)
            plume.add_color_stop_rgba(0, 0.72, 0.94, 1, 0.90)
            plume.add_color_stop_rgba(0.28, 0.20, 0.62, 1, 0.72)
            plume.add_color_stop_rgba(0.70, 1, 0.40, 0.12, 0.38)
            plume.add_color_stop_rgba(1, 1, 0.18, 0.03, 0)
            path(cr, [(-20, y - 3.5), (-25 - length, y), (-20, y + 3.5)])
            cr.set_source(plume)
            cr.fill()
            path(cr, [(-20, y - 1.4), (-22 - length * 0.65, y), (-20, y + 1.4)])
            cr.set_source_rgba(0.88, 0.98, 1, 0.95)
            cr.fill()
            # Travelling elliptical shock pulses radiate down each exhaust jet.
            for i in range(3):
                phase = (now * 5 + i / 3) % 1
                cr.save()
                cr.translate(-24 - phase * 36, y)
                cr.scale(0.42, 1)
                cr.set_source_rgba(0.35, 0.78, 1, (1 - phase) * 0.38)
                cr.set_line_width(1.3)
                cr.arc(0, 0, 2 + phase * 4, 0, math.tau)
                cr.stroke()
                cr.restore()
    alpha = 0.55 + 0.45 * abs(math.sin(now * 8)) if ship.invulnerable > 0 else 1
    hull = [(23, 0), (-15, -15), (-10, 0), (-15, 15)]
    path(cr, hull)
    metal = cairo.LinearGradient(-8, -15, 8, 15)
    metal.add_color_stop_rgba(0, 0.75, 0.85, 0.91, alpha)
    metal.add_color_stop_rgba(0.38, 0.32, 0.49, 0.61, alpha)
    metal.add_color_stop_rgba(0.55, 0.16, 0.30, 0.42, alpha)
    metal.add_color_stop_rgba(1, 0.055, 0.13, 0.23, alpha)
    cr.set_source(metal)
    cr.fill_preserve()
    cr.set_source_rgba(0.55, 0.86, 0.98, 0.80 * alpha)
    cr.set_line_width(1.1)
    cr.stroke()
    # Swept wing panels and a reinforced spine.
    for side, color in [(-1, (0.60, 0.74, 0.82)), (1, (0.12, 0.25, 0.35))]:
        path(cr, [(18, 0), (-13, side * 13), (-4, side * 4)])
        cr.set_source_rgba(*color, 0.78 * alpha)
        cr.fill()
        path(cr, [(-11, side * 11), (-2, side * 5)], False)
        cr.set_source_rgba(0.08, 0.13, 0.20, 0.65 * alpha)
        cr.set_line_width(0.75)
        cr.stroke()
    # Nacelles sit proud of the wings, with metallic housings and warm accents.
    for side in [-1, 1]:
        y = side * 10.5
        body = [
            (-21, y - 3.8),
            (-19, y - 4.4),
            (1, y - 3.2),
            (5, y),
            (1, y + 3.2),
            (-19, y + 4.4),
            (-21, y + 3.8),
        ]
        path(cr, body)
        shade = cairo.LinearGradient(0, y - 4, 0, y + 4)
        shade.add_color_stop_rgba(0, 0.70, 0.78, 0.83, alpha)
        shade.add_color_stop_rgba(0.4, 0.28, 0.41, 0.53, alpha)
        shade.add_color_stop_rgba(1, 0.05, 0.12, 0.19, alpha)
        cr.set_source(shade)
        cr.fill_preserve()
        cr.set_source_rgba(0.42, 0.64, 0.76, alpha)
        cr.set_line_width(0.8)
        cr.stroke()
        path(cr, [(-16, y), (-5, y)], False)
        cr.set_source_rgba(1, 0.61, 0.21, 0.9 * alpha)
        cr.set_line_width(1.1)
        cr.stroke()
        cr.set_source_rgba(0.03, 0.065, 0.095, alpha)
        cr.rectangle(-22, y - 2.8, 3, 5.6)
        cr.fill()
        cr.set_source_rgba(0.45, 0.9, 1, (0.9 if ship.thrust else 0.28) * alpha)
        cr.rectangle(-22.2, y - 1.8, 1.4, 3.6)
        cr.fill()
    # The visibly inset windshield reflects blue sky and a bright glass glint.
    canopy = [(15, 0), (5, -4.2), (-2, -3), (-2, 3), (5, 4.2)]
    path(cr, canopy)
    glass = cairo.LinearGradient(2, -4, 8, 4)
    glass.add_color_stop_rgba(0, 0.50, 0.96, 1, alpha)
    glass.add_color_stop_rgba(0.3, 0.06, 0.55, 0.72, alpha)
    glass.add_color_stop_rgba(0.7, 0.025, 0.23, 0.42, alpha)
    glass.add_color_stop_rgba(1, 0.01, 0.07, 0.17, alpha)
    cr.set_source(glass)
    cr.fill_preserve()
    cr.set_source_rgba(0.02, 0.07, 0.11, alpha)
    cr.set_line_width(1.1)
    cr.stroke()
    path(cr, [(0, -2), (5, -2.7), (10, -0.9)], False)
    cr.set_source_rgba(0.86, 1, 1, 0.85 * alpha)
    cr.set_line_width(0.85)
    cr.stroke()
    path(cr, [(5, -3.5), (5, 3.5)], False)
    cr.set_source_rgba(0.04, 0.13, 0.21, 0.8 * alpha)
    cr.set_line_width(0.65)
    cr.stroke()


    muzzle_flash(cr, ship.muzzle_flash, (.55, .94, 1))


def draw_enemy(cr, enemy, now):
    """Original fleet-inspired silhouettes: ring cruiser, winged raider, marauder."""
    r = enemy.radius
    color = FLEET_COLORS[enemy.kind]
    cr.rotate(math.atan2(enemy.velocity.y, enemy.velocity.x))
    cr.scale(r / 29, r / 29)
    pulse = 0.65 + 0.35 * math.sin(now * 19)
    glow(cr, 0, 0, 45, color, 0.12)
    if enemy.shield_remaining > 0:
        cr.set_source_rgba(.3, .85, 1, .6)
        cr.set_line_width(2)
        cr.arc(0, 0, 39, 0, math.tau)
        cr.stroke()

    def panel(points, light=1):
        path(cr, points)
        metal = cairo.LinearGradient(-12, -20, 14, 20)
        metal.add_color_stop_rgb(0, *(min(1, c * light * 0.85 + 0.15) for c in color))
        metal.add_color_stop_rgb(0.5, *(c * light * 0.42 for c in color))
        metal.add_color_stop_rgb(1, *(c * light * 0.14 for c in color))
        cr.set_source(metal)
        cr.fill_preserve()
        cr.set_source_rgba(*color, 0.9)
        cr.set_line_width(0.9)
        cr.stroke()

    def window(x, y, width=5):
        cr.set_source_rgb(0.58, 0.92, 1)
        cr.rectangle(x, y, width, 1.5)
        cr.fill()

    def engine(x, y):
        length = 22 + 12 * pulse + 4 * math.sin(now * 67 + y)
        glow(cr, x - 9, y, 25, color, .38 * pulse)
        plume = cairo.LinearGradient(x, y, x - length, y)
        plume.add_color_stop_rgba(0, .85, .98, 1, .95)
        plume.add_color_stop_rgba(.3, *color, .8)
        plume.add_color_stop_rgba(1, *color, 0)
        path(cr, [(x, y - 3), (x - length, y), (x, y + 3)])
        cr.set_source(plume)
        cr.fill()
        for i in range(3):
            phase = (now * 4 + i / 3) % 1
            cr.save()
            cr.translate(x - phase * length, y)
            cr.scale(.4, 1)
            cr.set_source_rgba(*color, (1 - phase) * .6)
            cr.set_line_width(1)
            cr.arc(0, 0, 2 + phase * 3, 0, math.tau)
            cr.stroke()
            cr.restore()
        cr.set_source_rgb(0.8, 0.98, 1)
        cr.arc(x, y, 1.6, 0, math.tau)
        cr.fill()

    if enemy.kind == "ring":
        # Blue science cruiser with a distinctive annular engine assembly.
        cr.save()
        cr.scale(0.55, 1)
        cr.arc(-8, 0, 24, 0, math.tau)
        cr.arc(-8, 0, 16, 0, math.tau)
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        metal = cairo.LinearGradient(-35, -24, 20, 24)
        metal.add_color_stop_rgb(0, 0.40, 0.69, 0.85)
        metal.add_color_stop_rgb(0.5, 0.12, 0.31, 0.48)
        metal.add_color_stop_rgb(1, 0.025, 0.10, 0.19)
        cr.set_source(metal)
        cr.fill()
        cr.set_fill_rule(cairo.FILL_RULE_WINDING)
        for radius in [17, 23]:
            cr.arc(-8, 0, radius, 0, math.tau)
            cr.set_source_rgba(*color, 0.95)
            cr.set_line_width(1.2)
            cr.stroke()
        cr.restore()
        panel([(-20, -3), (21, -6), (29, 0), (21, 6), (-20, 3)], 1.15)
        panel([(-7, -4), (5, -13), (10, -11), (3, -3)], 0.9)
        panel([(-7, 4), (5, 13), (10, 11), (3, 3)], 0.9)
        window(15, -2, 6)
        for y in [-13, 13]:
            engine(-13, y)
    elif enemy.kind == "raider":
        # Green angular battlecraft with swept wings and a forward bridge.
        for side in [-1, 1]:
            panel(
                [
                    (9, side * 3),
                    (-9, side * 9),
                    (-20, side * 26),
                    (-29, side * 22),
                    (-24, side * 7),
                    (-8, side * 2),
                ],
                1.1,
            )
            path(cr, [(-15, side * 12), (-23, side * 21)], False)
            cr.set_source_rgb(0.60, 0.95, 0.34)
            cr.set_line_width(1.4)
            cr.stroke()
            engine(-26, side * 20)
            window(-19, side * 11, 3)
        panel(
            [
                (-18, -4),
                (6, -5),
                (20, -10),
                (29, -4),
                (29, 4),
                (20, 10),
                (6, 5),
                (-18, 4),
            ],
            0.8,
        )
        panel([(15, -5), (26, -3), (26, 3), (15, 5)], 1.3)
        window(22, -1, 5)
        cr.set_source_rgb(1, 0.43, 0.14)
        cr.arc(27, 0, 1.4, 0, math.tau)
        cr.fill()
    else:
        # Red/copper trading warship: a broad crescent with forward prongs.
        panel(
            [
                (25, -18),
                (8, -28),
                (-14, -21),
                (-27, -7),
                (-27, 7),
                (-14, 21),
                (8, 28),
                (25, 18),
                (12, 9),
                (-3, 11),
                (-8, 0),
                (-3, -11),
                (12, -9),
            ],
            1.2,
        )
        panel([(-16, -5), (13, -7), (23, 0), (13, 7), (-16, 5)], 0.9)
        for side in [-1, 1]:
            path(cr, [(-10, side * 18), (6, side * 22), (19, side * 16)], False)
            cr.set_source_rgb(1, 0.67, 0.27)
            cr.set_line_width(1.5)
            cr.stroke()
            window(1, side * 15, 4)
            engine(-18, side * 13)
        window(13, -1.4, 6)
        cr.set_source_rgb(0.95, 0.69, 0.31)
        cr.arc(-3, 0, 3, 0, math.tau)
        cr.fill()


    muzzle_flash(cr, enemy.muzzle_flash, color)


def centered(cr, text, x, y, size, color, alpha=1):
    cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    ext = cr.text_extents(text)
    cr.set_source_rgba(*color, alpha)
    cr.move_to(x - ext.width / 2 - ext.x_bearing, y)
    cr.show_text(text)


def draw_core_part(cr, part, now):
    if part.kind != "core":
        color = {
            "shield": (0.3, 1, 0.55),
            "missile": (1, 0.5, 0.15),
            "blast": (0.8, 0.35, 1),
        }[part.kind]
        glow(cr, 0, 0, 30, color, 0.25)
        cr.set_source_rgb(*color)
        cr.set_line_width(2)
        if part.kind == "blast":
            cr.arc(0, 0, 11, 0, math.tau)
            cr.stroke()
            for angle in range(0, 360, 45):
                a = math.radians(angle)
                path(
                    cr,
                    [
                        (math.cos(a) * 4, math.sin(a) * 4),
                        (math.cos(a) * 16, math.sin(a) * 16),
                    ],
                    False,
                )
                cr.stroke()
            return
        if part.kind == "shield":
            path(cr, [(-10, -10), (10, -10), (9, 5), (0, 14), (-9, 5)])
        else:
            path(cr, [(0, -14), (7, -2), (5, 10), (-5, 10), (-7, -2)])
        cr.stroke()
        return
    fade = min(1, max(0, (now - part.born) * 2))
    pulse = 0.65 + 0.35 * math.sin(now * 4 + part.angle)
    glow(cr, 0, 0, 30, (0.12, 0.75, 1), (0.14 + 0.1 * pulse) * fade)
    cr.rotate(part.angle + now * 0.65)
    cr.set_line_width(0.85)
    cr.set_source_rgba(0.35, 0.85, 1, 0.36 * fade)
    cr.arc(0, 0, 16, 0, math.pi * 0.65)
    cr.stroke()
    cr.arc(0, 0, 16, math.pi, math.pi * 1.65)
    cr.stroke()
    path(cr, [(-8, -7), (8, -7), (11, 0), (8, 7), (-8, 7), (-11, 0)])
    shade = cairo.LinearGradient(0, -7, 0, 7)
    shade.add_color_stop_rgba(0, 0.55, 0.66, 0.74, fade)
    shade.add_color_stop_rgba(0.5, 0.16, 0.27, 0.36, fade)
    shade.add_color_stop_rgba(1, 0.04, 0.09, 0.16, fade)
    cr.set_source(shade)
    cr.fill_preserve()
    cr.set_source_rgba(0.48, 0.80, 0.94, 0.8 * fade)
    cr.stroke()
    for x in [-7, 5]:
        cr.rectangle(x, -5, 2, 10)
        cr.set_source_rgba(1, 0.69, 0.25, fade)
        cr.fill()
    cr.rectangle(-3, -5, 6, 10)
    cr.set_source_rgba(0.17, 0.84, 1, (0.7 + 0.3 * pulse) * fade)
    cr.fill()
    cr.rectangle(-1, -4, 2, 8)
    cr.set_source_rgba(0.81, 1, 1, fade)
    cr.fill()


def draw_core_status(cr, world):
    x = world.width / 2
    if world.warp_remaining > 0:
        return
    if world.part_flash > 0:
        centered(
            cr,
            f"WARP CORE {world.core_parts} / 5",
            x,
            world.height - 48,
            13,
            (0.54, 0.87, 0.96),
            min(1, world.part_flash * 2),
        )
    elif world.zone_flash > 0:
        names = {
            "ring": "BLUE RING FLEET",
            "raider": "GREEN RAIDER FLEET",
            "marauder": "RED MARAUDER FLEET",
        }
        centered(
            cr,
            f"SECTOR {world.zone+1}  /  {names[world.zone_fleet]}",
            x,
            world.height - 48,
            14,
            FLEET_COLORS[world.zone_fleet],
            min(1, world.zone_flash * 2),
        )


@lru_cache(maxsize=8)
def nebula_surface(color):
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 160, 160)
    cr = cairo.Context(surface)
    glow(cr, 80, 80, 78, color, 0.3)
    return surface


@lru_cache(maxsize=1)
def warp_echo_surface():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 160, 80)
    cr = cairo.Context(surface)
    cr.translate(80, 40)
    draw_ship(cr, Ship(invulnerable=0), 0)
    return surface


def draw_warp(cr, world):
    progress = 1 - world.warp_remaining / WARP_DURATION
    elapsed = WARP_DURATION - world.warp_remaining
    ramp = min(1, elapsed / 1.4)
    ramp = ramp * ramp * (3 - 2 * ramp)
    strength = math.sin(math.pi * progress) ** 0.65 * ramp
    # Keep the departure field visible as the drive spools up.
    fade = max(0, 1 - elapsed / 1.2)
    if fade > 0:
        cr.push_group()
        stars(cr, world)
        for rock in world.warp_rocks:
            p = rock.position - world.camera + Vec(world.width / 2, world.height / 2)
            if -120 < p.x < world.width + 120 and -120 < p.y < world.height + 120:
                surface = rock_surface(rock.radius, rock.outline)
                cr.save()
                cr.translate(p.x, p.y)
                cr.rotate(rock.angle)
                cr.set_source_surface(
                    surface, -surface.get_width() / 2, -surface.get_height() / 2
                )
                cr.paint()
                cr.restore()
        backdrop = cr.pop_group()
        cr.set_source(backdrop)
        cr.paint_with_alpha(fade)
    center = world.ship.position - world.camera + Vec(world.width / 2, world.height / 2)
    rng = random.Random(world.seed ^ 0x575250)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    unit = Vec(math.cos(world.warp_heading), math.sin(world.warp_heading))
    span = max(world.width, world.height) * 2
    sideways = Vec(-unit.y, unit.x)
    # Reference: icy white/blue light, lavender haze and deep indigo gaps.
    palette = [
        (0.28, 0.44, 1),
        (0.48, 0.40, 0.95),
        (0.58, 0.78, 1),
        (0.84, 0.90, 1),
        (0.38, 0.58, 1),
        (0.67, 0.52, 0.93),
        (0.35, 0.78, 0.92),
    ]
    elapsed = WARP_DURATION - world.warp_remaining
    travel = elapsed * (0.35 + progress * 0.85)
    # Soft stretched nebula clouds flow backwards in the same plane as the ship.
    for i in range(36):
        phase = (rng.random() - elapsed * (0.055 + rng.random() * 0.045)) % 1
        offset = rng.uniform(-span * 0.22, span * 0.22)
        offset += math.sin(elapsed * 0.65 + i * 1.7) * 35
        p = center + unit * ((phase - 0.5) * span) + sideways * offset
        color = palette[i % len(palette)]
        cr.save()
        cr.translate(p.x, p.y)
        cr.rotate(world.warp_heading)
        stretch = rng.uniform(2.8, 5.0)
        breadth = rng.uniform(0.7, 1.8)
        cr.scale(stretch, breadth)
        cloud = nebula_surface(color)
        cr.rectangle(-80, -80, 160, 160)
        cr.clip()
        cr.set_source_surface(cloud, -80, -80)
        cr.paint_with_alpha(strength * (0.65 + 0.2 * math.sin(elapsed * 1.2 + i)))
        cr.restore()
    # Three blur widths surround bright, fast, parallel star trails.
    for i in range(200):
        phase = (rng.random() - travel * (0.6 + rng.random() * 0.65)) % 1
        offset = rng.uniform(-span / 2, span / 2)
        length = (180 + rng.random() * 600) * (0.15 + strength)
        start = center + unit * ((phase - 0.5) * span) + sideways * offset
        end = start - unit * length
        if (
            max(start.x, end.x) < -40
            or min(start.x, end.x) > world.width + 40
            or max(start.y, end.y) < -40
            or min(start.y, end.y) > world.height + 40
        ):
            continue
        color = palette[i % len(palette)]
        alpha = (0.4 + rng.random() * 0.5) * (0.1 + strength * 0.9)
        streak = cairo.LinearGradient(end.x, end.y, start.x, start.y)
        streak.add_color_stop_rgba(0, *color, 0)
        streak.add_color_stop_rgba(0.65, *color, alpha * 0.65)
        streak.add_color_stop_rgba(1, *color, alpha)
        for width, opacity in [(26, 0.10), (7, 0.28)]:
            path(cr, [(end.x, end.y), (start.x, start.y)], False)
            cr.set_source_rgba(*color, alpha * opacity)
            cr.set_line_width(width)
            cr.stroke()
        path(cr, [(end.x, end.y), (start.x, start.y)], False)
        cr.set_source(streak)
        cr.set_line_width(1.5 + rng.random() * 1.5)
        cr.stroke()
        # White leading glint makes the direction of travel visible.
        head = start - unit * min(90, length * 0.2)
        path(cr, [(head.x, head.y), (start.x, start.y)], False)
        cr.set_source_rgba(0.85, 0.98, 1, alpha)
        cr.set_line_width(1.5)
        cr.stroke()
    cr.save()
    cr.translate(center.x, center.y)
    cr.rotate(world.ship.angle)
    # Long nacelle backblast and faint hull echoes sell the speed change.
    for y in [-10.5, 10.5]:
        beam = cairo.LinearGradient(-20, y, -100 - strength * 440, y)
        beam.add_color_stop_rgba(0, 0.72, 0.96, 1, 0.6 * strength)
        beam.add_color_stop_rgba(1, 0.06, 0.35, 1, 0)
        path(cr, [(-20, y - 5), (-100 - strength * 440, y), (-20, y + 5)])
        cr.set_source(beam)
        cr.fill()
    echo = warp_echo_surface()
    for i in [3, 2, 1]:
        cr.save()
        cr.translate(-i * strength * 28, 0)
        cr.rectangle(-80, -40, 160, 80)
        cr.clip()
        cr.set_source_surface(echo, -80, -40)
        cr.paint_with_alpha(0.22 * strength / i)
        cr.restore()
    draw_ship(cr, world.ship, world.time)
    cr.restore()
    centered(
        cr,
        "WARP ENGAGED",
        world.width / 2,
        world.height - 48,
        15,
        (0.66, 0.89, 1),
        min(1, strength * 2),
    )
    draw_core_status(cr, world)


def stars(cr, world):
    # Fixed stars in two parallax layers expose camera travel without a grid.
    for layer, factor in enumerate([0.22, 0.58]):
        camera = world.camera * factor
        cell = 330
        for x in range(
            math.floor((camera.x - world.width / 2) / cell) - 1,
            math.floor((camera.x + world.width / 2) / cell) + 2,
        ):
            for y in range(
                math.floor((camera.y - world.height / 2) / cell) - 1,
                math.floor((camera.y + world.height / 2) / cell) + 2,
            ):
                rng = random.Random(
                    (x * 73856093 ^ y * 19349663 ^ world.seed ^ layer * 83492791)
                    & ((1 << 64) - 1)
                )
                for _ in range(5):
                    sx, sy = (x + rng.random()) * cell - camera.x + world.width / 2, (
                        y + rng.random()
                    ) * cell - camera.y + world.height / 2
                    alpha = rng.uniform(0.15, 0.45)
                    cr.set_source_rgba(0.55, 0.68, 0.8, alpha)
                    cr.arc(sx, sy, rng.uniform(0.45, 1.1), 0, math.tau)
                    cr.fill()


def render(cr, world, width, height):
    cr.set_source_rgb(0, 0, 0)
    cr.paint()
    cr.save()
    cr.scale(width / world.width, height / world.height)
    cr.set_antialias(cairo.ANTIALIAS_BEST)
    if world.warp_remaining > 0:
        # Render the live ship and streaks at the same resolution as gameplay.
        draw_warp(cr, world)
        cr.restore()
        return
    stars(cr, world)
    jitter = Vec(
        math.sin(world.time * 93) * world.shake,
        math.cos(world.time * 117) * world.shake * 0.6,
    )

    def screen(position):
        return position - world.camera + Vec(world.width / 2, world.height / 2) + jitter

    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for rock in world.rocks:
        center = screen(rock.position)
        if not (
            -rock.radius - 20 < center.x < world.width + rock.radius + 20
            and -rock.radius - 20 < center.y < world.height + rock.radius + 20
        ):
            continue
        cr.save()
        cr.translate(center.x, center.y)
        cr.rotate(rock.angle)
        surface = rock_surface(rock.radius, rock.outline)
        cr.set_source_surface(
            surface, -surface.get_width() / 2, -surface.get_height() / 2
        )
        cr.paint()
        cr.restore()
    for part in world.parts:
        p = screen(part.position)
        if -35 < p.x < world.width + 35 and -35 < p.y < world.height + 35:
            cr.save()
            cr.translate(p.x, p.y)
            draw_core_part(cr, part, world.time)
            cr.restore()
    for spark in world.sparks:
        p = screen(spark.position)
        if not (-15 < p.x < world.width + 15 and -15 < p.y < world.height + 15):
            continue
        heat = spark.life / spark.maximum
        if spark.kind == "impact_boom":
            radius = spark.size * (1 - heat) + 3
            glow(cr, p.x, p.y, radius * 1.8, (1, .65, .2), heat * .7)
            cr.set_source_rgba(1, .9, .55, heat)
            cr.set_line_width(2 * heat + .5)
            cr.arc(p.x, p.y, radius, 0, math.tau)
            cr.stroke()
            continue
        if spark.kind == "impact":
            tail = p - spark.velocity.unit() * (3 + 8 * heat)
            cr.set_source_rgba(1, .7 + .3 * heat, .3 + .7 * heat, heat)
            cr.set_line_width(1.4 * heat + .4)
            path(cr, [(tail.x, tail.y), (p.x, p.y)], False)
            cr.stroke()
            continue
        color = (
            (1, 0.35 + 0.45 * heat, 0.06)
            if spark.kind == "exhaust"
            else (1, 0.4 + 0.5 * heat, 0.12 + 0.5 * heat)
        )
        if spark.kind == "core":
            color = (0.2, 0.86, 1)
        if spark.size > 2:
            glow(cr, p.x, p.y, spark.size * 4, color, 0.20 * heat)
        cr.set_source_rgba(*color, heat * 0.9)
        cr.arc(p.x, p.y, spark.size * heat, 0, math.tau)
        cr.fill()
    for shot in world.shots:
        p = screen(shot.position)
        tail = p - shot.velocity.unit() * (32 if shot.missile else 16)
        color = (shot.color or (1, 0.24, 0.35)) if shot.hostile else (0.55, 0.94, 1)
        if shot.missile:
            color = (1, 0.55, 0.15)
        cr.set_source_rgba(*color, 0.15)
        cr.set_line_width(7)
        path(cr, [(tail.x, tail.y), (p.x, p.y)], False)
        cr.stroke()
        cr.set_source_rgba(*color, 0.95)
        cr.set_line_width(2)
        path(cr, [(tail.x, tail.y), (p.x, p.y)], False)
        cr.stroke()
        cr.set_source_rgb(1, 1, 1)
        cr.arc(p.x, p.y, 1.8, 0, math.tau)
        cr.fill()
    for ufo in world.enemies:
        p = screen(ufo.position)
        cr.save()
        cr.translate(p.x, p.y)
        draw_enemy(cr, ufo, world.time)
        cr.restore()
    if world.blast is not None:
        wave = world.blast
        p = screen(wave.position)
        fade = min(1, max(0, wave.life / 0.35))
        glow(cr, p.x, p.y, max(30, wave.radius), (0.65, 0.16, 1), 0.18 * fade)
        for width, alpha in [(32, 0.06), (14, 0.2), (4, 0.9)]:
            cr.set_source_rgba(0.7, 0.4, 1, alpha * fade)
            cr.set_line_width(width)
            cr.arc(p.x, p.y, max(1, wave.radius), 0, math.tau)
            cr.stroke()
        cr.set_source_rgba(0.85, 1, 1, 0.85 * fade)
        cr.set_line_width(1.5)
        cr.arc(p.x, p.y, max(1, wave.radius - 5), 0, math.tau)
        cr.stroke()
    if not world.dead:
        ship = world.ship
        p = screen(ship.position)
        cr.save()
        cr.translate(p.x, p.y)
        cr.save()
        cr.rotate(ship.angle)
        draw_ship(cr, ship, world.time)
        cr.restore()
        if world.shield_remaining > 0:
            draw_shield(cr, world.time)
        cr.restore()
    if not world.dead:
        draw_core_status(cr, world)
    if world.dead:
        fade = min(1, (2.8 - world.restart_timer) * 3)
        cr.select_font_face(
            "sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL
        )

        def centered(text, y, size, color):
            cr.set_font_size(size)
            ext = cr.text_extents(text)
            cr.set_source_rgba(*color, fade)
            cr.move_to((world.width - ext.width) / 2 - ext.x_bearing, y)
            cr.show_text(text)

        centered("SHIP DESTROYED", world.height / 2 - 14, 30, (0.72, 0.9, 0.96))
        centered(
            f"SCORE {world.score:06d}    /    NEW FLIGHT",
            world.height / 2 + 24,
            15,
            (0.36, 0.58, 0.67),
        )
    cr.restore()
