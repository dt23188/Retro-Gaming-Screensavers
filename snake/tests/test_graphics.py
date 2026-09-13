import collections
import sys
import unittest

import cairo
from graphics import render_arena, smooth_centerline, curve_controls
from snake import Arena, Snake
from topology import Topology


class SpanningRenderTests(unittest.TestCase):
    def test_staircases_become_straight_diagonals_in_every_direction(self):
        staircase = [(0,0), (1,0), (1,1), (2,1), (2,2), (3,2)]
        for sx in (-1, 1):
            for sy in (-1, 1):
                points = smooth_centerline([(x*sx, y*sy) for x,y in staircase])
                for x, y in points:
                    self.assertAlmostEqual(x*sx-y*sy, .5)
                for a, b in zip(points, points[1:]):
                    self.assertAlmostEqual((b[0]-a[0])*sx, .5)
                    self.assertAlmostEqual((b[1]-a[1])*sy, .5)

    def test_straight_runs_are_unchanged(self):
        for points in [[(i,0) for i in range(6)], [(0,i) for i in range(6)]]:
            self.assertEqual(smooth_centerline(points), points)

    def test_diagonal_head_advances_evenly_between_moves(self):
        trail = [(i//2, (i+1)//2) for i in range(12)]
        heads = [smooth_centerline(list(reversed(trail[i-3:i+1])))[0]
                 for i in range(3,12)]
        for a, b in zip(heads, heads[1:]):
            self.assertEqual((b[0]-a[0], b[1]-a[1]), (.5,.5))

    def test_curves_share_a_tangent_at_each_join(self):
        points = smooth_centerline([(0,0), (1,0), (2,0), (2,1), (2,2)])
        for i in range(2, len(points)):
            _, incoming = curve_controls(points, i)
            outgoing, _ = curve_controls(points, i-1)
            p = points[i-1]
            for d in (0,1):
                self.assertAlmostEqual(p[d]-incoming[d], outgoing[d]-p[d])

    def test_entire_food_including_glow_fades_to_black(self):
        arena = Arena(12, 8, seed=1)
        actor = Snake(collections.deque([(0,0), (1,0), (2,0), (3,0)]), 0, [0])
        arena.snakes = {0: actor}
        arena.foods = {(8,5)}
        arena.food_born = {(8,5): 0}
        brightness = []
        for elapsed in (25, 27.5, 30):
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, 480, 320)
            render_arena(cairo.Context(surface), arena, {}, 1, 480, 320, 0, elapsed=elapsed)
            surface.flush()
            data = bytes(surface.get_data())
            # Includes the food's outer glow; the snake is outside this region.
            channels = (0, 1, 2) if sys.byteorder == 'little' else (1, 2, 3)
            brightness.append(sum(sum(data[y*surface.get_stride()+300*4+c:
                                           y*surface.get_stride()+380*4:4])
                                  for y in range(180,260) for c in channels))
        self.assertGreater(brightness[0], brightness[1])
        self.assertGreater(brightness[1], brightness[2])
        self.assertEqual(brightness[2], 0)

    def test_seam_is_one_continuous_snake_in_both_viewports(self):
        rectangles = [(0, 0, 400, 300), (400, 100, 400, 300)]
        topology = Topology(rectangles, 40)
        arena = Arena(topology.width, topology.height, seed=1, cells=topology.cells)
        actor = Snake(collections.deque([(10,4), (9,4), (8,4), (7,4)]), 0, [0])
        arena.snakes = {0: actor}
        arena.foods = set()
        previous = {0: (actor, [(9,4), (8,4), (7,4), (6,4)])}

        def picture(width, height, offset=(0, 0)):
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
            cr = cairo.Context(surface)
            cr.translate(-offset[0], -offset[1])
            render_arena(cr, arena, previous, .5, width, height, 0, topology=topology)
            surface.flush()
            return surface

        whole = picture(800, 400)
        whole_data = bytes(whole.get_data())
        for x, y, w, h in rectangles:
            view = picture(w, h, (x, y))
            actual = bytes(view.get_data())
            expected = b''.join(whole_data[(row+y)*whole.get_stride()+x*4:
                                         (row+y)*whole.get_stride()+(x+w)*4]
                                for row in range(h))
            self.assertEqual(actual, expected)
            # Each monitor shows part of the same head centered on the seam.
            self.assertGreater(sum(actual), 0)


if __name__ == '__main__':
    unittest.main()
