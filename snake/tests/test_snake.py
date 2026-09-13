import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location('snake', pathlib.Path(__file__).resolve().parents[1] / 'src' / 'snake.py')
snake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snake)


class GameTests(unittest.TestCase):
    def test_cycles(self):
        for w, h in [(4,4), (8,6), (24,16)]:
            path = snake.cycle(w,h)
            self.assertEqual(len(set(path)), w*h)
            for a,b in zip(path, path[1:]+path[:1]):
                self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]), 1)

    def test_ai_completes(self):
        for seed in range(12):
            game = snake.Game(12,8,seed)
            for _ in range(96*96):
                before = len(game.body)
                game.step()
                self.assertEqual(len(set(game.body)), len(game.body))
                self.assertIn(len(game.body), (before, before+1))
                self.assertNotIn(game.food, game.body)
                if game.state != 'playing':
                    break
            self.assertEqual(game.state, 'won', seed)
            self.assertEqual(len(game.body),96)

    def test_full_size(self):
        game = snake.Game(seed=42)
        for _ in range(384*384):
            game.step()
            if game.state != 'playing':
                break
        self.assertEqual(game.state,'won')

    def test_collision(self):
        for target in [(-1,0), (99,99)]:
            game = snake.Game(seed=1)
            game.step(target)
            self.assertEqual(game.state, 'lost')
        game = snake.Game(seed=1)
        game.step(game.body[1])
        self.assertEqual(game.state, 'lost')

    def test_food_tracking_regression(self):
        # This open-board position previously took 140 moves to reach food.
        game = snake.Game(69,38,seed=0)
        for _ in range(112):
            game.step()
            # Body order must remain intact for safe late-game completion.
            order = [(game.index[p]-game.index[game.body[-1]]) % len(game.path)
                     for p in reversed(game.body)]
            self.assertEqual(order, sorted(set(order)))
            if len(game.body) > 4:
                break
        self.assertEqual(len(game.body), 5)
        self.assertLessEqual(game.steps, 112)
        old_food = game.route_food
        game.choose()
        self.assertNotEqual(game.route_food, old_food)
        self.assertEqual(game.route_food, game.food)

    def test_terminal_sizes(self):
        for cols, rows in [(80,24), (160,60), (240,60), (90,160), (191,53), (8,4)]:
            w, h = snake.board_size((cols, rows))
            game = snake.Game(w, h)
            self.assertEqual(h % 2, 0)
            covered = set()
            for y in range(h):
                for x in range(w):
                    x0, y0, x1, y1 = snake.cell_bounds(x, y, game, (cols, rows))
                    self.assertGreater(x1, x0)
                    self.assertGreater(y1, y0)
                    cells = {(cx, cy) for cx in range(x0,x1) for cy in range(y0,y1)}
                    self.assertFalse(cells & covered)
                    covered.update(cells)
            self.assertEqual(len(covered), cols * rows)
            output = snake.frame(game,1,0,(cols,rows),0)
            self.assertNotIn('12;23;21', output)
            self.assertNotIn('10;19;18', output)
            self.assertNotIn('S N A K E', output)

    def test_tiny_terminal(self):
        self.assertIsNone(snake.board_size((7,3)))
        self.assertIn('48;2;0;0;0m', snake.frame(snake.Game(),1,0,(7,3),0))


class ArenaTests(unittest.TestCase):
    def test_food_fades_expires_and_relocates(self):
        game = snake.Arena(seed=42)
        original = next(iter(game.foods))
        for elapsed, alpha in [(0,1), (25,1), (27.5,.5), (30,0)]:
            self.assertEqual(game.food_opacity(original, elapsed), alpha)
        game.expire_food(30)
        game.populate_food(1)
        self.assertNotIn(original, game.foods)
        self.assertEqual(len(game.foods), 1)
        replacement = next(iter(game.foods))
        self.assertEqual(game.food_born[replacement], 30)
        self.assertEqual(game.food_opacity(replacement, 30), 1)
        game.expire_food(59.9)
        self.assertIn(original, game.food_cooldown)
        game.expire_food(60)
        self.assertNotIn(original, game.food_cooldown)

    def test_food_lifetime_after_resize_uses_current_clock(self):
        game = snake.Arena(seed=42, elapsed=120)
        food = next(iter(game.foods))
        game.expire_food(120)
        self.assertIn(food, game.foods)
        self.assertEqual(game.food_opacity(food, 145), 1)
        game.expire_food(150)
        self.assertNotIn(food, game.foods)

    def test_elapsed_time_expires_food_even_without_regular_steps(self):
        game = snake.Arena(seed=42)
        old = set(game.foods)
        game.step(300)
        self.assertTrue(game.foods.isdisjoint(old))
        self.assertEqual(set(game.food_born), game.foods)
        self.assertTrue(all(born == 300 for born in game.food_born.values()))

    def test_timed_population(self):
        game = snake.Arena(seed=42)
        self.assertEqual((len(game.snakes), len(game.foods)), (1, 1))
        for elapsed, population in [(7.9, (1, 1)), (8, (1, 2)),
                                    (20, (2, 3)), (100, (6, 12)), (10000, (6, 12))]:
            game.step(elapsed)
            self.assertEqual((len(game.snakes), len(game.foods)), population)

    def test_shared_food_has_one_winner(self):
        game = snake.Arena(12, 8, seed=2)
        game.snakes = {
            0: snake.Snake(snake.collections.deque([(3,3),(2,3),(1,3),(0,3)]), 0, [0]),
            1: snake.Snake(snake.collections.deque([(5,3),(6,3),(7,3),(8,3)]), 1, [0]),
        }
        game.foods = {(4,3)}
        eaten = game.step(0)
        self.assertEqual(eaten, [(4,3)])
        self.assertEqual(sorted(len(a.body) for a in game.snakes.values()), [4,5])
        self.assertEqual(sum((4,3) in a.body for a in game.snakes.values()), 1)

    def test_long_running_competition(self):
        for width, height in [(4,4), (12,8), (40,24)]:
            game = snake.Arena(width, height, seed=19)
            consumed = 0
            for tick in range(2400):
                previous = {i: (a, list(a.body)) for i, a in game.snakes.items()}
                consumed += len(game.step(tick / 14))
                cells = [p for a in game.snakes.values() for p in a.body]
                self.assertEqual(len(cells), len(set(cells)))
                self.assertTrue(set(cells) <= game.cells)
                self.assertTrue(game.foods.isdisjoint(cells))
                for identity, actor in game.snakes.items():
                    for a, b in zip(actor.body, list(actor.body)[1:]):
                        self.assertEqual(abs(a[0]-b[0])+abs(a[1]-b[1]), 1)
                    old_actor, old_body = previous.get(identity, (None, []))
                    if old_actor is actor:
                        a, b = old_body[0], actor.body[0]
                        self.assertLessEqual(abs(a[0]-b[0])+abs(a[1]-b[1]), 1)
            self.assertGreater(consumed, 20)


if __name__ == '__main__':
    unittest.main()
