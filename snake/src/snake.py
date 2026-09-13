#!/usr/bin/env python3
"""Omarchy Snake: dependency-free terminal animation and autonomous game engine."""
import argparse
import collections
import json
import heapq
import os
import random
import select
import shutil
import signal
import subprocess
import sys
import time


def cycle(width, height):
    """Closed path visiting every cell once (height must be even)."""
    if width < 4 or height < 4 or height % 2:
        raise ValueError('board needs width >= 4 and even height >= 4')
    path = [(x, 0) for x in range(width)]
    for y in range(1, height):
        path.extend((x, y) for x in (range(width - 1, 0, -1) if y % 2 else range(1, width)))
    path.extend((0, y) for y in range(height - 1, 0, -1))
    return path


class Game:
    def __init__(self, width=24, height=16, seed=None):
        self.width, self.height = width, height
        self.path = cycle(width, height)
        self.index = {p: i for i, p in enumerate(self.path)}
        self.rng = random.Random(seed)
        start = self.rng.randrange(len(self.path))
        self.body = collections.deque(self.path[(start - i) % len(self.path)] for i in range(4))
        self.steps = 0
        self.state = 'playing'
        self.strategy = 'SEEKING'
        self.food_route = {}
        self.route_food = None
        self.retry_route_at = 0
        self.food = self.spawn_food()

    def spawn_food(self):
        free = sorted(set(self.path) - set(self.body))
        return self.rng.choice(free) if free else None

    def plan_food_route(self):
        """Find a short food route without breaking the body's cycle order.

        Every edge advances along the free arc between head and tail. This
        preserves the completion guarantee while allowing geometric pathfinding.
        Cache the route until food changes; bound search work on large displays.
        """
        head = self.body[0]
        n = len(self.path)
        origin = self.index[head]
        offset = lambda p: (self.index[p] - origin) % n
        food_gap, tail_gap = offset(self.food), offset(self.body[-1])
        if not 0 < food_gap < tail_gap:
            return {}
        heuristic = lambda p: abs(p[0]-self.food[0]) + abs(p[1]-self.food[1])
        queue = [(heuristic(head), 0, head)]
        costs, parent = {head: 0}, {}
        expansions = 0
        while queue and expansions < 4096:
            _, cost, current = heapq.heappop(queue)
            if cost != costs[current]:
                continue
            if current == self.food:
                route = {}
                while current != head:
                    previous = parent[current]
                    route[previous] = current
                    current = previous
                return route
            expansions += 1
            x, y = current
            for target in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):
                if target not in self.index or not offset(current) < offset(target) <= food_gap:
                    continue
                distance = cost + 1
                if distance < costs.get(target, float('inf')):
                    costs[target] = distance
                    parent[target] = current
                    heapq.heappush(queue, (distance+heuristic(target), distance, target))
        return {}

    def choose(self):
        head = self.body[0]
        n = len(self.path)
        distance = lambda p: (self.index[p] - self.index[head]) % n
        tail_gap = distance(self.body[-1])
        food_gap = distance(self.food)
        # Keep the body ordered along a Hamiltonian cycle. A shortcut cannot
        # overtake either the tail or food. Dense boards follow the cycle.
        candidates = [self.path[(self.index[head] + 1) % n]]
        if len(self.body) < n * 0.65:
            x, y = head
            candidates += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        safe = [p for p in candidates if p in self.index and
                0 < distance(p) < tail_gap and distance(p) <= food_gap]
        if self.food != self.route_food:
            self.food_route = {}
            self.route_food = self.food
            self.retry_route_at = 0
        if len(self.body) < n * 0.65:
            if head not in self.food_route and self.steps >= self.retry_route_at:
                self.food_route = self.plan_food_route()
                self.retry_route_at = self.steps + 16
            planned = self.food_route.get(head)
            if planned in safe:
                self.strategy = 'TRACKING FOOD'
                return planned
        target = max(safe, key=distance) if safe else candidates[0]
        self.strategy = 'SHORTCUT' if distance(target) > 1 else 'FOLLOWING CYCLE'
        return target

    def step(self, target=None):
        if self.state != 'playing':
            return
        target = self.choose() if target is None else target
        growing = target == self.food
        occupied = set(self.body if growing else list(self.body)[:-1])
        head = self.body[0]
        if (target not in self.index or target in occupied or
                abs(target[0] - head[0]) + abs(target[1] - head[1]) != 1):
            self.state = 'lost'
            return
        self.body.appendleft(target)
        self.steps += 1
        if growing:
            self.food = self.spawn_food()
            if self.food is None:
                self.state = 'won'
        else:
            self.body.pop()


Snake = collections.namedtuple('Snake', 'body identity stalled')


class Arena:
    """An ongoing shared-food competition, ramped by elapsed seconds."""
    FOOD_LIFETIME = 30.0
    FOOD_FADE = 5.0
    FOOD_COOLDOWN = 30.0

    def __init__(self, width=24, height=16, seed=None, cells=None, elapsed=0):
        self.width, self.height = width, height
        self.irregular = cells is not None
        self.path = sorted(cells) if self.irregular else cycle(width, height)
        self.cells = set(self.path)
        self.rng = random.Random(seed)
        self.snakes = {}
        self.foods = set()
        self.elapsed = elapsed
        self.food_born = {}
        self.food_cooldown = {}
        self.steps = 0
        self.spawn_snake(0)
        self.populate_food(1)

    def occupied(self):
        return {p for actor in self.snakes.values() for p in actor.body}

    def spawn_snake(self, identity):
        occupied = self.occupied() | self.foods
        starts = list(range(len(self.path)))
        self.rng.shuffle(starts)
        for start in starts:
            if self.irregular:
                # Irregular monitor unions need not have a Hamiltonian cycle.
                # Find a four-cell chain without crossing a missing display.
                def extend(chain):
                    if len(chain) == 4:
                        return chain
                    adjacent = self.neighbors(chain[-1])
                    self.rng.shuffle(adjacent)
                    for p in adjacent:
                        if p not in occupied and p not in chain:
                            result = extend(chain + [p])
                            if result:
                                return result
                    return None
                head = self.path[start]
                chain = extend([head]) if head not in occupied else None
                if chain is None:
                    continue
                body = collections.deque(chain)
            else:
                body = collections.deque(self.path[(start-i) % len(self.path)] for i in range(4))
            if occupied.isdisjoint(body):
                actor = Snake(body, identity, [0])
                self.snakes[identity] = actor
                return True
        return False

    def populate_food(self, target):
        needed = target - len(self.foods)
        if needed <= 0:
            return
        free = sorted(self.cells - self.occupied() - self.foods - self.food_cooldown.keys())
        for p in self.rng.sample(free, min(needed, len(free))):
            self.foods.add(p)
            self.food_born[p] = self.elapsed

    def food_opacity(self, p, elapsed):
        if p not in self.foods:
            return 0.0
        age = max(0, elapsed - self.food_born.get(p, self.elapsed))
        remaining = max(0.0, min(1.0, (self.FOOD_LIFETIME-age)/self.FOOD_FADE))
        return remaining * remaining * (3-2*remaining)

    def expire_food(self, elapsed):
        self.elapsed = max(self.elapsed, elapsed)
        self.food_cooldown = {p: until for p, until in self.food_cooldown.items()
                              if until > self.elapsed}
        self.food_born = {p: self.food_born.get(p, self.elapsed) for p in self.foods}
        for p, born in list(self.food_born.items()):
            if self.elapsed-born >= self.FOOD_LIFETIME:
                self.foods.remove(p)
                del self.food_born[p]
                self.food_cooldown[p] = self.elapsed + self.FOOD_COOLDOWN

    def neighbors(self, p):
        x, y = p
        return [(a, b) for a, b in ((x+1,y), (x-1,y), (x,y+1), (x,y-1))
                if (a, b) in self.cells]

    def choose(self, actor):
        # Replan against current shared occupancy: earlier moves reserve their
        # cells, preventing head-on collisions and double consumption.
        blocked = self.occupied() - {actor.body[-1]}
        head = actor.body[0]
        queue = collections.deque([head])
        first = {head: None}
        while queue and len(first) < 4096:
            current = queue.popleft()
            if current in self.foods:
                return first[current]
            adjacent = self.neighbors(current)
            self.rng.shuffle(adjacent)
            for p in adjacent:
                if p not in blocked and p not in first:
                    first[p] = p if current == head else first[current]
                    queue.append(p)
        safe = [p for p in self.neighbors(head) if p not in blocked]
        # When food is enclosed, keep moving toward open space.
        return max(safe, key=lambda p: sum(n not in blocked for n in self.neighbors(p)),
                   default=None)

    def step(self, elapsed):
        self.expire_food(elapsed)
        snake_target = min(6, 1 + int(max(0, elapsed) // 20), max(1, len(self.path)//24))
        food_target = min(12, 1 + int(max(0, elapsed) // 8), max(1, len(self.path)//8))
        for identity in range(snake_target):
            if identity not in self.snakes:
                self.spawn_snake(identity)
        self.populate_food(food_target)
        eaten = []
        actors = list(self.snakes.values())
        # Rotate priority so no snake always wins a contested cell.
        shift = self.steps % len(actors) if actors else 0
        for actor in actors[shift:] + actors[:shift]:
            target = self.choose(actor)
            if target is None:
                actor.stalled[0] += 1
                if actor.stalled[0] >= 14:
                    del self.snakes[actor.identity]
                    self.spawn_snake(actor.identity)
                continue
            actor.stalled[0] = 0
            actor.body.appendleft(target)
            if target in self.foods:
                self.foods.remove(target)
                self.food_born.pop(target, None)
                eaten.append(target)
                # Bound growth so the screensaver stays lively indefinitely.
                if len(actor.body) > max(6, min(48, len(self.path)//(snake_target*4))):
                    actor.body.pop()
            else:
                actor.body.pop()
        self.populate_food(food_target)
        self.steps += 1
        return eaten


def hypr(*args):
    try:
        result = subprocess.run(['hyprctl', *args], capture_output=True, text=True, timeout=0.5)
        return result.stdout if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def cursor(hidden):
    value = 'true' if hidden else 'false'
    if hypr('eval', 'hl.config({ cursor = { invisible = ' + value + ' } })') is None:
        hypr('keyword', 'cursor:invisible', value)


def board_size(size):
    """Roughly square cells, with an even row count for the AI cycle."""
    cols, rows = size
    if cols < 8 or rows < 4:
        return None
    return max(4, cols // 4), max(4, (rows // 2) // 2 * 2)


def cell_bounds(x, y, game, size):
    # Partition all terminal columns/rows, including division remainders.
    # This reaches every edge on ultrawide, portrait and odd-sized terminals.
    cols, rows = size
    return (x * cols // game.width, y * rows // game.height,
            (x + 1) * cols // game.width, (y + 1) * rows // game.height)


def frame(game, episode, best, size, now):
    cols, rows = size
    out = ['\x1b[H\x1b[0m\x1b[48;2;0;0;0m\x1b[2J']
    if board_size(size) is None:
        return ''.join(out)

    def block(p, rgb):
        x0, y0, x1, y1 = cell_bounds(*p, game, size)
        for y in range(y0, y1):
            out.append(f'\x1b[{y+1};{x0+1}H\x1b[48;2;{rgb}m' + ' ' * (x1-x0))

    if game.food is not None:
        block(game.food, '255;184;92' if int(now * 3) % 2 else '218;134;63')
    for i, p in enumerate(game.body):
        fade = i / max(1, len(game.body)-1)
        rgb = ('215;255;226' if i == 0 else
               f'{int(40-22*fade)};{int(204-105*fade)};{int(135-63*fade)}')
        block(p, '222;92;92' if game.state == 'lost' else rgb)

    # No permanent HUD or reserved margins: the entire display is playable.
    if game.state != 'playing':
        message = ('BOARD COMPLETE' if game.state == 'won' else 'GAME OVER')
        message += f'  /  SCORE {len(game.body)-4}  /  RESTARTING'
        message = message[:cols]
        out.append(f'\x1b[{max(1, rows//2)};{max(1, (cols-len(message))//2+1)}H'
                   f'\x1b[48;2;0;0;0m\x1b[38;2;103;232;169m{message}')
    out.append('\x1b[0m')
    return ''.join(out)


def run(args):
    import termios
    import tty
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise SystemExit('Run in a terminal, or use the fullscreen launcher.')
    old = termios.tcgetattr(sys.stdin)
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
        signal.signal(sig, stop)
    # Let fullscreen terminal geometry arrive before choosing the board.
    if not args.preview:
        time.sleep(0.4)
    size = shutil.get_terminal_size()
    width, height = board_size(size) or (4, 4)
    game = Game(width, height, args.seed)
    episode, best = 1, 0
    next_step = time.monotonic() + 1
    check_at = time.monotonic() + 1.5
    last_pointer = None
    finished_at = None
    try:
        tty.setraw(sys.stdin)
        sys.stdout.write('\x1b[?1049h\x1b[?7l\x1b[?25l\x1b[?1003h\x1b[?1006h\x1b]11;#000000\x07')
        if not args.preview:
            cursor(True)
        while not stopping:
            now = time.monotonic()
            if args.duration and now >= started + args.duration:
                break
            if select.select([sys.stdin], [], [], 0)[0]:
                os.read(sys.stdin.fileno(), 4096)
                break
            if not args.preview and now >= check_at:
                active = hypr('activewindow', '-j')
                pointer = hypr('cursorpos', '-j')
                try:
                    if active is not None and json.loads(active).get('class') != 'org.omarchy.screensaver':
                        break
                    if pointer is not None:
                        current = json.loads(pointer)
                        if last_pointer is not None and current != last_pointer:
                            break
                        last_pointer = current
                except (ValueError, AttributeError):
                    pass
                check_at = now + 0.25
            size = shutil.get_terminal_size()
            dimensions = board_size(size)
            if dimensions is not None and dimensions != (width, height):
                # Rebuild the safe AI route when the grid changes. A fresh round
                # avoids cropping the snake or creating a collision on resize.
                width, height = dimensions
                game = Game(width, height)
                episode += 1
                finished_at = None
                next_step = now + 0.3
            if dimensions is not None and now >= next_step:
                if game.state == 'playing':
                    game.step()
                    best = max(best, len(game.body)-4)
                elif finished_at is None:
                    finished_at = now
                elif now - finished_at >= 3:
                    episode += 1
                    game = Game(width, height)
                    finished_at = None
                next_step = now + 1 / args.speed
            sys.stdout.write(frame(game, episode, best, size, now))
            sys.stdout.flush()
            time.sleep(1/30)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        sys.stdout.write('\x1b[?1003l\x1b[?1006l\x1b[?7h\x1b[?25h\x1b[0m\x1b]111\x07\x1b[?1049l')
        sys.stdout.flush()
        if not args.preview:
            cursor(False)
            subprocess.run(['pkill', '-f', '[o]rg.omarchy.screensaver'], check=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', action='store_true', help='run only in this terminal; do not manage Omarchy windows')
    parser.add_argument('--speed', type=float, default=18, help='moves per second (default 18)')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--duration', type=float, help='automatically exit after this many seconds')
    args = parser.parse_args()
    if not 1 <= args.speed <= 120:
        parser.error('--speed must be between 1 and 120')
    started = time.monotonic()
    run(args)
