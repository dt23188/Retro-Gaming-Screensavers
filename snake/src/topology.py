"""Exact display-edge geometry for a shared, irregular Snake board.

Rectangles are supplied in the compositor's logical coordinate space (after
scaling and rotation), not physical monitor pixels. Every monitor edge is a
grid line, so even a partial shared edge connects only its actual overlap.
"""


class Topology:
    def __init__(self, rectangles, cell_size=28):
        self.rectangles = tuple(tuple(r) for r in rectangles)
        if not self.rectangles or cell_size <= 0:
            raise ValueError('at least one display and a positive cell size are required')
        if any(w <= 0 or h <= 0 for x, y, w, h in self.rectangles):
            raise ValueError('display dimensions must be positive')

        def axis(edges):
            edges = sorted(set(edges))
            result = []
            for low, high in zip(edges, edges[1:]):
                count = max(1, round((high-low)/cell_size))
                result.extend(low+(high-low)*i/count for i in range(count))
            return result + [edges[-1]]

        self.x_edges = axis([a for x, y, w, h in self.rectangles for a in (x, x+w)])
        self.y_edges = axis([a for x, y, w, h in self.rectangles for a in (y, y+h)])
        self.width, self.height = len(self.x_edges)-1, len(self.y_edges)-1
        self.centers = {}
        self.units = {}
        # Iterate the rectangles rather than the bounding box; holes/gaps have
        # no cells and cannot become shortcuts or food/spawn locations.
        for x, y, w, h in self.rectangles:
            x0, x1 = self.x_edges.index(x), self.x_edges.index(x+w)
            y0, y1 = self.y_edges.index(y), self.y_edges.index(y+h)
            for cy in range(y0, y1):
                for cx in range(x0, x1):
                    left, right = self.x_edges[cx:cx+2]
                    top, bottom = self.y_edges[cy:cy+2]
                    self.centers[cx, cy] = ((left+right)/2, (top+bottom)/2)
                    self.units[cx, cy] = min(right-left, bottom-top)
        self.cells = set(self.centers)

    def center(self, cell):
        return self.centers[cell]
