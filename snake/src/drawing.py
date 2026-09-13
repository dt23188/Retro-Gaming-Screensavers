"""Shared visual renderer; Cairo on GTK, compatible QPainter backend on Qt."""
import math
import colorsys
from types import SimpleNamespace
from curves import smooth_centerline, curve_controls

def disc(cr, x, y, radius, color):
    cr.set_source_rgba(*color)
    cr.arc(x, y, radius, 0, math.tau)
    cr.fill()


def render(cr, game, previous, fraction, width, height, now, sparks=(), clear=True, hue=0, backend=None):
    if backend is None:
        import cairo as backend
    if clear:
        cr.set_source_rgb(0, 0, 0)
        cr.paint()
    def tint(r, g, b):
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return colorsys.hsv_to_rgb((h+hue) % 1, s, v)
    cr.set_antialias(backend.ANTIALIAS_BEST)
    sx, sy = width / game.width, height / game.height
    unit = min(sx, sy)
    center = getattr(game, 'center', lambda p: ((p[0]+.5)*sx, (p[1]+.5)*sy))
    unit_at = getattr(game, 'unit_at', lambda p: min(sx, sy))
    old_points = smooth_centerline([center(p) for p in previous])
    current_points = smooth_centerline([center(p) for p in game.body])
    points = []
    for i, (cx, cy) in enumerate(current_points):
        ox, oy = old_points[min(i, len(old_points)-1)]
        points.append((ox + (cx-ox)*fraction, oy + (cy-oy)*fraction))

    for food in getattr(game, 'foods', [game.food] if game.food is not None else []):
        alpha = getattr(game, 'food_alpha', {}).get(food, 1.0)
        if alpha <= 0:
            continue
        x, y = center(food)
        unit = unit_at(food)
        radius = unit * (.22 + .018*math.sin(now*3))
        glow = backend.RadialGradient(x, y, radius*.4, x, y, unit*.85)
        glow.add_color_stop_rgba(0, 1, .48, .10, .23*alpha)
        glow.add_color_stop_rgba(1, 1, .35, .02, 0)
        cr.set_source(glow)
        cr.arc(x, y, unit*.85, 0, math.tau)
        cr.fill()
        orb = backend.RadialGradient(x-radius*.3, y-radius*.4, 0, x, y, radius)
        orb.add_color_stop_rgba(0, 1, .91, .64, alpha)
        orb.add_color_stop_rgba(.45, 1, .66, .24, alpha)
        orb.add_color_stop_rgba(1, .90, .30, .055, alpha)
        cr.set_source(orb)
        cr.arc(x, y, radius, 0, math.tau)
        cr.fill()
        disc(cr, x-radius*.28, y-radius*.35, radius*.16, (1, 1, .9, .75*alpha))

    cr.set_line_cap(backend.LINE_CAP_ROUND)
    cr.set_line_join(backend.LINE_JOIN_ROUND)
    # Smooth diagonal runs and curve the remaining bends. Adjacent cubic
    # segments share tangents, so the body has no angular joins.
    for i in range(len(points)-1, 0, -1):
        a, b = points[i], points[i-1]
        unit = min(unit_at(game.body[i]), unit_at(game.body[i-1]))
        t = 1 - i / len(points)
        thickness = unit * (.32 + .27 * min(1, t*3))
        c1, c2 = curve_controls(points, i)
        cr.move_to(*a)
        cr.curve_to(*c1, *c2, *b)
        cr.set_line_width(thickness + unit*.17)
        cr.set_source_rgba(*tint(.08, .85, .45), .07)
        cr.stroke_preserve()
        cr.set_line_width(thickness)
        grad = backend.LinearGradient(a[0], a[1]-thickness/2, b[0], b[1]+thickness/2)
        if game.state == 'lost':
            grad.add_color_stop_rgb(0, .95, .35, .32)
            grad.add_color_stop_rgb(1, .5, .08, .08)
        else:
            grad.add_color_stop_rgb(0, *tint(.12+.10*t, .53+.33*t, .33+.24*t))
            grad.add_color_stop_rgb(1, *tint(.025, .23+.30*t, .16+.16*t))
        cr.set_source(grad)
        cr.stroke()
    x, y = points[0]
    unit = unit_at(game.body[0])
    r = unit*.32
    head = backend.RadialGradient(x-r*.3, y-r*.4, 0, x, y, r)
    head.add_color_stop_rgb(0, *tint(.65, 1, .79))
    head.add_color_stop_rgb(1, *tint(.10, .69, .40))
    cr.set_source(head)
    cr.arc(x, y, r, 0, math.tau)
    cr.fill()
    dx, dy = points[0][0]-points[1][0], points[0][1]-points[1][1]
    length = math.hypot(dx, dy) or 1
    dx, dy = dx/length, dy/length
    for sign in (-1, 1):
        ex = x + dx*r*.35 - dy*r*.46*sign
        ey = y + dy*r*.35 + dx*r*.46*sign
        disc(cr, ex, ey, r*.21, (.015, .09, .065, 1))
        disc(cr, ex+dx*r*.055, ey+dy*r*.055, r*.065, (.8, 1, .9, .9))
    for px, py, born in sparks:
        spark_x, spark_y = center((px, py))
        unit = unit_at((px, py))
        age = now-born
        if 0 <= age < .6:
            for i in range(8):
                angle = i*math.tau/8
                distance = unit*(.3+age*1.5)
                disc(cr, spark_x+math.cos(angle)*distance,
                     spark_y+math.sin(angle)*distance,
                     unit*.045*(1-age/.6), (1, .65, .25, (1-age/.6)*.8))
    if game.state != 'playing':
        text = 'BOARD COMPLETE' if game.state == 'won' else 'GAME OVER'
        cr.select_font_face('sans-serif', backend.FONT_SLANT_NORMAL, backend.FONT_WEIGHT_NORMAL)
        cr.set_font_size(24)
        ext = cr.text_extents(text)
        cr.move_to((width-ext.width)/2, height/2)
        cr.set_source_rgb(.6, .85, .7)
        cr.show_text(text)


def render_arena(cr, arena, previous, fraction, width, height, now, sparks=(), topology=None,
                 elapsed=None, backend=None):
    elapsed = arena.elapsed if elapsed is None else elapsed
    cr.set_source_rgb(0, 0, 0)
    cr.paint()
    cr.save()
    if topology:
        for rectangle in topology.rectangles:
            cr.rectangle(*rectangle)
        cr.clip()
    for i, actor in enumerate(arena.snakes.values()):
        old_actor, old_body = previous.get(actor.identity, (None, list(actor.body)))
        # A new or respawned snake appears in place, without crossing the board.
        if old_actor is not actor:
            old_body = list(actor.body)
        view = SimpleNamespace(width=arena.width, height=arena.height,
                               body=actor.body, food=None, state='playing',
                               foods=sorted(arena.foods) if i == 0 else [])
        view.food_alpha = {p: arena.food_opacity(p, elapsed) for p in view.foods}
        if topology is not None:
            view.center = topology.center
            view.unit_at = topology.units.__getitem__
        render(cr, view, old_body, fraction, width, height, now,
               sparks if i == 0 else (), clear=False, hue=actor.identity / 6, backend=backend)
    cr.restore()
