import collections
import unittest

from snake import Arena, Snake
from topology import Topology


def reachable(game, start):
    found, queue = {start}, collections.deque([start])
    while queue:
        for p in game.neighbors(queue.popleft()):
            if p not in found:
                found.add(p)
                queue.append(p)
    return found


class TopologyTests(unittest.TestCase):
    def arena(self, rectangles, cell=100):
        topology = Topology(rectangles, cell)
        return topology, Arena(topology.width, topology.height, seed=42, cells=topology.cells)

    def test_offset_shared_edge_and_exposed_walls(self):
        topology, game = self.arena([(-400, 0, 400, 300), (0, 100, 400, 300)])
        self.assertNotIn((4, 0), game.neighbors((3, 0)))
        self.assertIn((4, 1), game.neighbors((3, 1)))
        self.assertIn((4, 2), game.neighbors((3, 2)))
        self.assertNotIn((3, 3), game.neighbors((4, 3)))
        self.assertEqual(reachable(game, (0, 0)), topology.cells)
        self.assertNotIn((-1, 0), game.neighbors((0, 0)))
        self.assertNotIn((8, 2), game.neighbors((7, 2)))

    def test_snake_crosses_seam_to_eat(self):
        _, game = self.arena([(-400, 0, 400, 300), (0, 100, 400, 300)])
        actor = Snake(collections.deque([(3,1), (2,1), (1,1), (0,1)]), 0, [0])
        game.snakes = {0: actor}
        game.foods = {(4,1)}
        self.assertEqual(game.step(0), [(4,1)])
        self.assertEqual(actor.body[0], (4,1))
        self.assertIn((3,1), actor.body)

    def test_gaps_and_corner_contacts_are_not_portals(self):
        for second in [(401,0,400,300), (400,300,400,300)]:
            topology, game = self.arena([(0,0,400,300), second])
            left = reachable(game, (0,0))
            self.assertLess(len(left), len(topology.cells))
            self.assertTrue(all(topology.center(p)[0] < 400 for p in left))

    def test_saved_stacked_layout(self):
        topology, game = self.arena([(0,0,3840,2160), (200,2160,3440,1440)], 28)
        self.assertEqual(reachable(game, min(game.cells)), game.cells)
        seam_y = topology.y_edges.index(2160)
        crossings = [topology.center(p)[0] for p in game.cells
                     if p[1] == seam_y-1 and (p[0], seam_y) in game.neighbors(p)]
        self.assertTrue(crossings)
        self.assertTrue(all(200 < x < 3640 for x in crossings))
        # An exposed portion of the upper display cannot lead into the void.
        for p in game.cells:
            if p[1] == seam_y-1 and not 200 < topology.center(p)[0] < 3640:
                self.assertNotIn((p[0], seam_y), game.neighbors(p))

    def test_fractional_logical_geometry_and_mirroring(self):
        # GDK provides already scaled/rotated logical dimensions.
        rectangles = [(-853, -640, 853, 640), (0, -640, 720, 1280)]
        topology, game = self.arena(rectangles, 28)
        duplicate = Topology(rectangles + [rectangles[0]], 28)
        self.assertEqual(topology.cells, duplicate.cells)
        self.assertEqual(reachable(game, min(game.cells)), game.cells)
        area = sum((topology.x_edges[x+1]-topology.x_edges[x]) *
                   (topology.y_edges[y+1]-topology.y_edges[y]) for x,y in game.cells)
        self.assertAlmostEqual(area, 853*640 + 720*1280)

    def test_competition_stays_inside_irregular_union(self):
        topology, game = self.arena([(0,0,400,300), (400,100,400,300)], 28)
        for tick in range(1600):
            game.step(120 + tick/14)
            bodies = [p for actor in game.snakes.values() for p in actor.body]
            self.assertEqual(len(bodies), len(set(bodies)))
            self.assertTrue(set(bodies) <= topology.cells)
            self.assertTrue(game.foods <= topology.cells)
            self.assertTrue(game.foods.isdisjoint(bodies))
            for actor in game.snakes.values():
                for a, b in zip(actor.body, list(actor.body)[1:]):
                    self.assertIn(b, game.neighbors(a))


if __name__ == '__main__':
    unittest.main()
