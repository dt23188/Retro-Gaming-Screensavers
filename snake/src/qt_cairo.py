"""Small QPainter adapter for the shared renderer's Cairo drawing vocabulary."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QBrush, QPen, QPainterPath, QPainter, QRadialGradient, QLinearGradient

ANTIALIAS_BEST = LINE_CAP_ROUND = LINE_JOIN_ROUND = 1


def color(*rgba):
    return QColor.fromRgbF(*rgba)


class Gradient:
    def add_color_stop_rgb(self, offset, r, g, b):
        self.value.setColorAt(offset, color(r, g, b))

    def add_color_stop_rgba(self, offset, r, g, b, a):
        self.value.setColorAt(offset, color(r, g, b, a))


class RadialGradient(Gradient):
    def __init__(self, x0, y0, r0, x1, y1, r1):
        self.value = QRadialGradient(QPointF(x1, y1), r1, QPointF(x0, y0), r0)


class LinearGradient(Gradient):
    def __init__(self, x0, y0, x1, y1):
        self.value = QLinearGradient(x0, y0, x1, y1)


class Context:
    def __init__(self, painter):
        self.painter = painter
        self.path = QPainterPath()
        self.brush = QBrush(Qt.GlobalColor.black)
        self.width = 1
        self.stack = []

    def set_source_rgb(self, *rgb):
        self.brush = QBrush(color(*rgb))

    set_source_rgba = set_source_rgb

    def set_source(self, gradient):
        self.brush = QBrush(gradient.value)

    def paint(self):
        self.painter.save()
        self.painter.resetTransform()
        self.painter.fillRect(self.painter.viewport(), self.brush)
        self.painter.restore()

    def set_antialias(self, _):
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    def arc(self, x, y, radius, start, end):
        # All arcs in the shared renderer are full circles.
        self.path.addEllipse(QRectF(x-radius, y-radius, radius*2, radius*2))

    def fill(self):
        self.painter.fillPath(self.path, self.brush)
        self.path = QPainterPath()

    def move_to(self, x, y):
        self.path.moveTo(x, y)

    def line_to(self, x, y):
        self.path.lineTo(x, y)

    def curve_to(self, *coordinates):
        self.path.cubicTo(*coordinates)

    def set_line_width(self, width):
        self.width = width

    def set_line_cap(self, _):
        pass

    def set_line_join(self, _):
        pass

    def stroke_preserve(self):
        self.painter.strokePath(self.path, QPen(self.brush, self.width, Qt.PenStyle.SolidLine,
                                              Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

    def stroke(self):
        self.stroke_preserve()
        self.path = QPainterPath()

    def rectangle(self, *rectangle):
        self.path.addRect(QRectF(*rectangle))

    def clip(self):
        self.path.setFillRule(Qt.FillRule.WindingFill)
        self.painter.setClipPath(self.path, Qt.ClipOperation.IntersectClip)
        self.path = QPainterPath()

    def save(self):
        self.painter.save()
        self.stack.append((self.brush, self.width))

    def restore(self):
        self.painter.restore()
        self.brush, self.width = self.stack.pop()
