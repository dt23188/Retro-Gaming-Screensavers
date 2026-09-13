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

# Cairo-compatible image caching, text, clipping and groups for Asteroids.
import math
from types import SimpleNamespace
from PySide6.QtGui import QImage, QFont, QFontMetricsF
FORMAT_ARGB32 = FORMAT_RGB24 = 0
FONT_SLANT_NORMAL = FONT_WEIGHT_NORMAL = 0
FILL_RULE_EVEN_ODD, FILL_RULE_WINDING = 0, 1

class ImageSurface:
    def __init__(self, fmt, width, height):
        self.image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        self.image.fill(Qt.GlobalColor.transparent)
    def get_width(self): return self.image.width()
    def get_height(self): return self.image.height()
    def write_to_png(self, path):
        if not self.image.save(str(path), 'PNG'): raise OSError('Cannot write '+str(path))

BaseContext = Context
class Context(BaseContext):
    def __init__(self, target):
        self.owns_painter = isinstance(target, ImageSurface)
        super().__init__(QPainter(target.image) if self.owns_painter else target)
        self.surface_source = None
        self.groups = []
        self.fill_rule = Qt.FillRule.WindingFill
    def __del__(self):
        if self.owns_painter and self.painter.isActive(): self.painter.end()
    def set_source_rgb(self, *rgb):
        self.surface_source = None
        super().set_source_rgb(*rgb)
    set_source_rgba = set_source_rgb
    def set_source(self, value):
        self.surface_source = (value.image, 0, 0) if isinstance(value, ImageSurface) else None
        if self.surface_source is None: super().set_source(value)
    def set_source_surface(self, surface, x, y): self.surface_source = (surface.image, x, y)
    def paint(self):
        if self.surface_source:
            image,x,y = self.surface_source
            self.painter.drawImage(QPointF(x,y),image)
        else: super().paint()
    def paint_with_alpha(self, alpha):
        self.painter.save(); self.painter.setOpacity(alpha); self.paint(); self.painter.restore()
    def arc(self, x,y,r,start,end):
        rect=QRectF(x-r,y-r,2*r,2*r)
        if abs(end-start)>=math.tau-1e-6: self.path.addEllipse(rect)
        else:
            point=QPointF(x+r*math.cos(start),y+r*math.sin(start))
            if self.path.isEmpty(): self.path.moveTo(point)
            else: self.path.lineTo(point)
            self.path.arcTo(rect,-math.degrees(start),-math.degrees(end-start))
    def close_path(self): self.path.closeSubpath()
    def fill_preserve(self):
        self.path.setFillRule(self.fill_rule)
        self.painter.fillPath(self.path,self.brush)
    def fill(self): self.fill_preserve(); self.path=QPainterPath()
    def set_fill_rule(self, rule): self.fill_rule=Qt.FillRule.OddEvenFill if rule==FILL_RULE_EVEN_ODD else Qt.FillRule.WindingFill
    def clip(self):
        self.path.setFillRule(self.fill_rule)
        self.painter.setClipPath(self.path,Qt.ClipOperation.IntersectClip)
        self.path=QPainterPath()
    def translate(self,x,y): self.painter.translate(x,y)
    def scale(self,x,y): self.painter.scale(x,y)
    def rotate(self,angle): self.painter.rotate(math.degrees(angle))
    def select_font_face(self, family, *_): self.painter.setFont(QFont(family))
    def set_font_size(self,size):
        font=self.painter.font(); font.setPointSizeF(size*72/self.painter.device().logicalDpiY()); self.painter.setFont(font)
    def text_extents(self,text):
        metrics=QFontMetricsF(self.painter.font());rect=metrics.boundingRect(text)
        return SimpleNamespace(width=rect.width(),height=rect.height(),x_bearing=rect.x(),y_bearing=rect.y())
    def show_text(self,text):
        self.painter.setPen(QPen(self.brush,1));self.painter.drawText(self.path.currentPosition(),text);self.path=QPainterPath()
    def push_group(self):
        image=ImageSurface(0,self.painter.viewport().width(),self.painter.viewport().height())
        original=self.painter; self.groups.append((original,image))
        self.painter=QPainter(image.image)
        self.painter.setTransform(original.transform())
        self.painter.setRenderHints(original.renderHints())
        self.painter.setFont(original.font())
    def pop_group(self):
        self.painter.end(); self.painter,image=self.groups.pop();return image
