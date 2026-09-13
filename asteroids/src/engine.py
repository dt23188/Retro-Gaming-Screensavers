"""Display-independent, fixed-step Asteroids simulation in an unbounded world."""

from collections import OrderedDict
from dataclasses import dataclass, field
import math
import random

TAU = math.tau
CHUNK = 640.0
RADII = (17.0, 31.0, 57.0)
POINTS = (100, 50, 20)
MAX_ROCKS = 180
MAX_PARTICLES = 600
MAX_PARTS = 16
WARP_DURATION = 15.0
CAMERA_FOLLOW_RATE = 2.5
CAMERA_TRAIL_SECONDS = 0.35
CAMERA_ROAM_FRACTION = 0.18
FLEET_COLORS = {
    "ring": (0.20, 0.65, 1.0),
    "raider": (0.32, 0.92, 0.44),
    "marauder": (1.0, 0.28, 0.24),
}


@dataclass
class Vec:
    x: float = 0.0
    y: float = 0.0

    def __add__(self, other):
        return Vec(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec(self.x - other.x, self.y - other.y)

    def __mul__(self, value):
        return Vec(self.x * value, self.y * value)

    def length(self):
        return math.hypot(self.x, self.y)

    def unit(self):
        return self * (1 / max(self.length(), 1e-9))

    def dot(self, other):
        return self.x * other.x + self.y * other.y


def direction(angle):
    return Vec(math.cos(angle), math.sin(angle))


def angle_delta(target, current):
    return (target - current + math.pi) % TAU - math.pi


def segment_hit(start, end, center, radius):
    """Earliest swept-circle hit, including a shot beginning inside a target."""
    d, p = end - start, start - center
    c = p.dot(p) - radius * radius
    if c <= 0:
        return 0.0
    a = d.dot(d)
    if a < 1e-12:
        return None
    b = p.dot(d)
    discriminant = b * b - a * c
    if discriminant < 0:
        return None
    t = (-b - math.sqrt(discriminant)) / a
    return t if 0 <= t <= 1 else None


def intercept(relative, velocity, speed=820.0):
    a, b, c = (
        velocity.dot(velocity) - speed * speed,
        2 * relative.dot(velocity),
        relative.dot(relative),
    )
    if abs(a) < 1e-9:
        times = [-c / b] if abs(b) > 1e-9 else []
    else:
        disc = b * b - 4 * a * c
        times = (
            [(-b - math.sqrt(disc)) / (2 * a), (-b + math.sqrt(disc)) / (2 * a)]
            if disc >= 0
            else []
        )
    valid = [t for t in times if 0 < t < 1.5]
    return relative + velocity * min(valid) if valid else relative


@dataclass
class Rock:
    position: Vec
    velocity: Vec
    tier: int
    angle: float
    spin: float
    outline: tuple

    @property
    def radius(self):
        return RADII[self.tier]


@dataclass
class Shot:
    position: Vec
    velocity: Vec
    life: float = 1.5
    hostile: bool = False
    previous: Vec = field(default_factory=Vec)
    color: tuple | None = None
    missile: bool = False


@dataclass
class Spark:
    position: Vec
    velocity: Vec
    life: float
    maximum: float
    kind: str
    size: float


@dataclass
class CorePart:
    position: Vec
    angle: float = 0.0
    born: float = 0.0
    kind: str = "core"


@dataclass
class RadialBlast:
    position: Vec
    camera: Vec
    width: int
    height: int
    maximum: float
    radius: float = 0.0
    life: float = 1.6


@dataclass
class Ship:
    position: Vec = field(default_factory=Vec)
    velocity: Vec = field(default_factory=lambda: Vec(119, -42.5))
    angle: float = -0.25
    thrust: bool = False
    invulnerable: float = 2.0


@dataclass
class Saucer:
    position: Vec
    velocity: Vec
    small: bool
    cooldown: float = 1.2
    life: float = 13.5
    kind: str = "ring"

    @property
    def radius(self):
        return 17 if self.small else 29


class World:
    """Thrust/inertia, rotating aim, four player shots, splitting rocks and UFOs.

    Space is streamed in deterministic sectors. The viewport follows the ship;
    neither the ship nor the rocks wrap at a window edge.
    """

    def __init__(self, seed=0, width=1280, height=900, start_in_warp=False):
        self.seed, self.width, self.height = seed, width, height
        self.rng = random.Random(seed)
        self.session = 0
        self.fleet_bag = []
        self.warps = 0
        self.parts_collected = 0
        self.core_parts = 0
        self.core_spawn_timer = self.rng.uniform(42, 52)
        self.power_spawn_timer = self.rng.uniform(25, 40)
        self.total_distance = 0.0
        self.deaths = 0
        self.shots_fired = 0
        self.rocks_hit = 0
        self.reset()
        self.opening_warp = start_in_warp
        if start_in_warp:
            self.core_parts = 5
            self.start_warp()

    def reset(self):
        self.zone = 0
        self.zone_fleet = self.next_fleet_kind()
        self.parts = []
        self.warp_remaining = 0.0
        self.warp_origin = self.warp_destination = Vec()
        self.warp_heading = 0.0
        self.part_flash = self.zone_flash = 0.0
        self.part_timer = 0.0
        self.shield_remaining = 0.0
        self.missile_ammo = 0
        self.shield_charges = 0
        self.blast_charges = 0
        self.blast = None
        self.missile_timer = 0.0
        self.powerup_wait = 0.0
        self.part_rng = random.Random(self.seed ^ (self.session * 0xA511E9B3))
        self.ship = Ship()
        self.camera = Vec()
        self.rocks, self.shots, self.sparks = [], [], []
        self.sectors = OrderedDict()
        self.saucer = None
        self.saucer_timer = self.rng.uniform(3, 6)
        self.time = self.score = self.kills = 0
        self.dead = False
        self.restart_timer = 0.0
        self.fire_timer = self.exhaust_timer = self.stream_timer = 0.0
        self.route_angle = self.rng.uniform(-math.pi, math.pi)
        self.route_timer = 0.0
        self.shake = 0.0
        self.stream()
        self.replenish_parts()

    def resize(self, width, height):
        self.width, self.height = max(100, width), max(100, height)
        self.stream_timer = 0

    def sector_seed(self, x, y):
        return (
            (self.seed + self.session * 0x9E3779B97F4A7C15)
            ^ (self.zone * 0xD6E8FEB86659FD93)
            ^ (x * 0x517CC1B727220A95)
            ^ (y * 0x6C8E9CF570932BD5)
        ) & ((1 << 64) - 1)

    def make_rock(self, position, tier=2, velocity=None, rng=None):
        rng = rng or self.rng
        angle = rng.uniform(0, TAU)
        velocity = velocity or direction(angle) * rng.uniform(20.4, 55.25)
        outline = tuple(rng.uniform(0.70, 1.06) for _ in range(rng.randint(9, 13)))
        return Rock(
            position,
            velocity,
            tier,
            rng.uniform(0, TAU),
            rng.uniform(-0.51, 0.51),
            outline,
        )

    def stream(self):
        self.parts = [
            part
            for part in self.parts
            if abs(part.position.x - self.camera.x) < self.width / 2 + 1200
            and abs(part.position.y - self.camera.y) < self.height / 2 + 1200
        ]
        self.rocks = [
            r
            for r in self.rocks
            if abs(r.position.x - self.camera.x) < self.width / 2 + 1600
            and abs(r.position.y - self.camera.y) < self.height / 2 + 1600
        ]
        margin = 780
        xmin, xmax = math.floor(
            (self.camera.x - self.width / 2 - margin) / CHUNK
        ), math.floor((self.camera.x + self.width / 2 + margin) / CHUNK)
        ymin, ymax = math.floor(
            (self.camera.y - self.height / 2 - margin) / CHUNK
        ), math.floor((self.camera.y + self.height / 2 + margin) / CHUNK)
        keys = [(x, y) for x in range(xmin, xmax + 1) for y in range(ymin, ymax + 1)]
        keys.sort(
            key=lambda p: ((p[0] + 0.5) * CHUNK - self.camera.x) ** 2
            + ((p[1] + 0.5) * CHUNK - self.camera.y) ** 2
        )
        for key in keys:
            if key in self.sectors:
                self.sectors.move_to_end(key)
                continue
            self.sectors[key] = True
            rng = random.Random(self.sector_seed(*key))
            count = rng.randint(2, 4) + min(2, int(self.time // 60))
            for _ in range(count):
                position = Vec(
                    (key[0] + rng.random()) * CHUNK, (key[1] + rng.random()) * CHUNK
                )
                if (position - self.ship.position).length() < 230 or len(
                    self.rocks
                ) >= MAX_ROCKS:
                    continue
                self.rocks.append(
                    self.make_rock(
                        position, rng.choices([0, 1, 2], [1, 2, 7])[0], rng=rng
                    )
                )
        while len(self.sectors) > 512:
            self.sectors.popitem(last=False)
        self.rocks = [
            r
            for r in self.rocks
            if abs(r.position.x - self.camera.x) < self.width / 2 + 1600
            and abs(r.position.y - self.camera.y) < self.height / 2 + 1600
        ]

    def part_location_safe(self, position):
        return all(
            (rock.position - position).length() > rock.radius + 65
            for rock in self.rocks
        )

    def spawn_pickup(self, kind):
        for _ in range(40):
            position = self.ship.position + direction(
                self.ship.angle + self.part_rng.uniform(-1.0, 1.0)
            ) * self.part_rng.uniform(160, 330)
            if self.part_location_safe(position):
                self.parts.append(
                    CorePart(position, self.part_rng.uniform(0, TAU), self.time, kind)
                )
                return True
        return False

    def replenish_parts(self):
        # One outstanding core at a time; the persistent clock survives respawns.
        if self.core_spawn_timer <= 0 and not any(p.kind == "core" for p in self.parts):
            self.spawn_pickup("core")

    def collect_parts(self, dt, previous=None):
        if self.dead or self.warp_remaining > 0:
            return
        previous = previous or self.ship.position
        for part in list(self.parts):
            distance = (part.position - self.ship.position).length()
            if distance < 105:
                # A short tractor pull catches pickups while the ship has inertia.
                part.position = part.position + (
                    self.ship.position - part.position
                ).unit() * min(distance, 330 * dt)
            if segment_hit(previous, self.ship.position, part.position, 28) is not None:
                self.parts.remove(part)
                self.emit(part.position, 8, "core")
                if part.kind == "shield":
                    self.shield_charges += 1
                elif part.kind == "blast":
                    self.blast_charges += 1
                    self.powerup_wait = 0.0
                elif part.kind == "missile":
                    self.missile_ammo += 8
                else:
                    self.core_parts += 1
                    self.parts_collected += 1
                    self.core_spawn_timer = self.rng.uniform(42, 52)
                    self.part_flash = 1.5
                    if self.core_parts >= 5:
                        self.start_warp()
                        break

    def start_warp(self):
        if self.dead or self.warp_remaining > 0 or self.core_parts < 5:
            return False
        self.warp_remaining = WARP_DURATION
        self.warp_origin = Vec(self.ship.position.x, self.ship.position.y)
        velocity = self.ship.velocity
        self.warp_heading = (
            math.atan2(velocity.y, velocity.x)
            if velocity.length() > 20
            else self.ship.angle
        )
        self.warp_initial_angle = self.ship.angle
        self.warp_initial_speed = velocity.length()
        self.warp_screen_offset = self.ship.position - self.camera
        self.warp_rocks = list(self.rocks)
        self.warp_destination = self.warp_origin + direction(
            self.warp_heading
        ) * self.part_rng.uniform(90000, 180000)
        self.ship.thrust = True
        self.rocks, self.parts, self.shots, self.sparks = [], [], [], []
        self.saucer = None
        self.shake = 0
        self.blast = None
        return True

    def update_warp(self, dt):
        self.warp_remaining = max(0, self.warp_remaining - dt)
        progress = 1 - self.warp_remaining / WARP_DURATION
        eased = progress * progress * (3 - 2 * progress)
        distance = (self.warp_destination - self.warp_origin).length()
        eased += (
            self.warp_initial_speed
            * WARP_DURATION
            / distance
            * (progress**3 - 2 * progress**2 + progress)
        )
        eased += 178.5 * WARP_DURATION / distance * (progress**3 - progress**2)
        position = self.warp_origin + (self.warp_destination - self.warp_origin) * eased
        self.total_distance += (position - self.ship.position).length()
        self.ship.position = position
        elapsed = WARP_DURATION - self.warp_remaining
        heading = direction(self.warp_heading)
        edge_distance = min(
            self.width * 0.38 / max(abs(heading.x), 0.001),
            self.height * 0.38 / max(abs(heading.y), 0.001),
        )
        edge_offset = heading * edge_distance
        if elapsed < 0.8:
            t = elapsed / 0.8
            blend = t * t * (3 - 2 * t)
            offset = (
                self.warp_screen_offset
                + (edge_offset - self.warp_screen_offset) * blend
            )
        elif elapsed < 2.6:
            t = (elapsed - 0.8) / 1.8
            blend = t * t * (3 - 2 * t)
            offset = edge_offset * (1 - blend)
        else:
            # Keep drifting during the long cruise instead of pinning the ship
            # to the same screen pixels after the departure rush recenters it.
            cruise_distance = min(
                178.5 * (CAMERA_TRAIL_SECONDS + 1 / CAMERA_FOLLOW_RATE),
                min(self.width, self.height) * CAMERA_ROAM_FRACTION,
            )
            offset = heading * (cruise_distance * (1 - math.exp(-(elapsed - 2.6) / 3)))
        self.camera = position - offset
        t = min(1, elapsed / 0.8)
        blend = t * t * (3 - 2 * t)
        self.ship.angle = (
            self.warp_initial_angle
            + angle_delta(self.warp_heading, self.warp_initial_angle) * blend
        )
        if self.warp_remaining == 0:
            self.finish_warp()

    def finish_warp(self):
        previous_fleet = self.zone_fleet
        self.zone += 1
        self.warps += 1
        self.zone_fleet = self.next_fleet_kind()
        if self.zone_fleet == previous_fleet:
            self.zone_fleet = self.next_fleet_kind()
        self.core_parts = 0
        self.part_flash = 0
        self.zone_flash = 2.5
        self.ship.position = Vec(self.warp_destination.x, self.warp_destination.y)
        self.ship.velocity = direction(self.warp_heading) * 178.5
        self.ship.invulnerable = 2.5
        # Keep the final warp framing; normal tracking takes over without a snap.
        self.sectors.clear()
        self.rocks, self.parts, self.shots, self.sparks = [], [], [], []
        self.saucer = None
        self.saucer_timer = self.rng.uniform(2, 4)
        self.part_rng = random.Random(
            self.seed ^ self.session * 0xA511E9B3 ^ self.zone * 0x45D9F3B
        )
        self.stream()
        if self.opening_warp:
            self.create_arrival_belt()
            self.opening_warp = False
        self.replenish_parts()
        self.stream_timer = 0.35
        self.part_timer = 1.0

    def create_arrival_belt(self):
        forward = direction(self.warp_heading)
        side = Vec(-forward.y, forward.x)
        for i in range(40):
            position = (
                self.ship.position
                + forward * self.part_rng.uniform(290, 470)
                + side * ((i - 19.5) * 42 + self.part_rng.uniform(-30, 30))
            )
            self.rocks.append(
                self.make_rock(
                    position,
                    self.part_rng.choices([0, 1, 2], [2, 3, 5])[0],
                    rng=self.part_rng,
                )
            )
        self.rocks = self.rocks[-MAX_ROCKS:]

    def emit(self, position, count, kind="explosion", velocity=None):
        velocity = velocity or Vec()
        for _ in range(count):
            speed = (
                self.rng.uniform(30, 225)
                if kind != "exhaust"
                else self.rng.uniform(30, 85)
            )
            motion = direction(self.rng.uniform(0, TAU)) * speed + velocity
            life = (
                self.rng.uniform(0.2, 0.9)
                if kind != "exhaust"
                else self.rng.uniform(0.16, 0.45)
            )
            self.sparks.append(
                Spark(
                    Vec(position.x, position.y),
                    motion,
                    life,
                    life,
                    kind,
                    self.rng.uniform(1, 3.5),
                )
            )
        self.sparks = self.sparks[-MAX_PARTICLES:]

    def split_rock(self, rock, award=True):
        if rock not in self.rocks:
            return
        self.rocks.remove(rock)
        if award:
            self.score += POINTS[rock.tier]
            self.kills += 1
            self.rocks_hit += 1
        self.shake = max(self.shake, 4 + rock.tier * 2)
        self.emit(rock.position, 12 + rock.tier * 9)
        if rock.tier:
            offset = direction(self.rng.uniform(0, TAU))
            for sign in [-1, 1]:
                velocity = rock.velocity + offset * (
                    sign * self.rng.uniform(38.25, 76.5)
                )
                self.rocks.append(
                    self.make_rock(
                        rock.position + offset * (sign * 8), rock.tier - 1, velocity
                    )
                )
        self.rocks = self.rocks[-MAX_ROCKS:]

    def destroy_ship(self):
        if (
            self.dead
            or self.warp_remaining > 0
            or self.ship.invulnerable > 0
            or self.shield_remaining > 0
        ):
            return
        self.dead = True
        self.deaths += 1
        self.restart_timer = 2.8
        self.shake = 25
        self.ship.thrust = False
        self.emit(self.ship.position, 100, velocity=self.ship.velocity * 0.4)

    def autopilot(self, dt):
        ship = self.ship
        self.route_timer -= dt
        if self.route_timer <= 0:
            self.route_angle += self.rng.uniform(-0.8, 0.8)
            self.route_timer = self.rng.uniform(4, 8)
        hazards = []
        for rock in self.rocks:
            relative, motion = (
                rock.position - ship.position,
                rock.velocity - ship.velocity,
            )
            t = max(0, min(1.4, -relative.dot(motion) / max(motion.dot(motion), 1)))
            distance = (relative + motion * t).length()
            if distance < rock.radius + 65 and relative.length() < 450:
                hazards.append((distance, relative, rock.radius))
        target = self.saucer
        candidates = [
            r for r in self.rocks if 85 < (r.position - ship.position).length() < 850
        ]
        if target is None and candidates:
            target = min(
                candidates,
                key=lambda r: (r.position - ship.position).length()
                * (
                    1
                    + abs(
                        angle_delta(
                            math.atan2(
                                r.position.y - ship.position.y,
                                r.position.x - ship.position.x,
                            ),
                            ship.angle,
                        )
                    )
                    * 0.4
                ),
            )
        aim = (
            intercept(target.position - ship.position, target.velocity)
            if target
            else direction(self.route_angle)
        )
        part_target = min(
            self.parts,
            key=lambda p: (p.position - ship.position).length(),
            default=None,
        )
        if part_target and (part_target.position - ship.position).length() > 1000:
            part_target = None
        if hazards:
            _, nearest, radius = min(hazards, key=lambda item: item[0])
            # Turn into a tangential escape, rather than stop travelling to aim.
            escape = nearest.unit() * -1
            route = (
                (part_target.position - ship.position).unit()
                if part_target
                else direction(self.route_angle)
            )
            heading = escape * 1.8 + route * 0.8
            desired = math.atan2(heading.y, heading.x)
            ship.thrust = True
        elif part_target and (
            self.time % 5 < 4 or (part_target.position - ship.position).length() < 250
        ):
            relative = part_target.position - ship.position
            desired_velocity = relative.unit() * min(
                246.5, max(59.5, relative.length() * 1.02)
            )
            steering = desired_velocity - ship.velocity * 0.85
            desired = math.atan2(steering.y, steering.x)
            ship.thrust = True
        elif target and self.time % 6 < 3.8:
            desired = math.atan2(aim.y, aim.x)
            ship.thrust = (
                ship.velocity.length() < 212.5
                or abs(angle_delta(desired, ship.angle)) < 0.4
                and self.time % 3 < 1.8
            )
        else:
            desired = self.route_angle
            ship.thrust = True
        error = angle_delta(desired, ship.angle)
        ship.angle += max(-3.7 * dt, min(3.7 * dt, error))
        if target and abs(angle_delta(math.atan2(aim.y, aim.x), ship.angle)) < 0.16:
            self.fire()

    def fire(self):
        if (
            self.fire_timer > 0
            or sum(not s.hostile and not s.missile for s in self.shots) >= 4
            or self.dead
            or self.warp_remaining > 0
        ):
            return
        nose = self.ship.position + direction(self.ship.angle) * 23
        self.shots.append(
            Shot(
                nose,
                # Blaster rounds follow the nose, without sideways ship drift.
                direction(self.ship.angle) * 820,
                previous=nose,
            )
        )
        self.fire_timer = 0.14
        self.shots_fired += 1

    def visible(self, position, radius=0, camera=None, width=None, height=None):
        camera = camera or self.camera
        return (
            abs(position.x - camera.x) <= (width or self.width) / 2 + radius
            and abs(position.y - camera.y) <= (height or self.height) / 2 + radius
        )

    def destroy_enemy(self):
        enemy = self.saucer
        if enemy is None:
            return
        self.score += 1000 if enemy.small else 200
        self.emit(enemy.position, 45)
        if len(self.parts) < MAX_PARTS and self.rng.random() < 0.35:
            kind = self.rng.choices(
                ["missile", "shield", "core", "blast"], [35, 35, 25, 5]
            )[0]
            self.parts.append(
                CorePart(
                    Vec(enemy.position.x, enemy.position.y),
                    self.rng.uniform(0, TAU),
                    self.time,
                    kind,
                )
            )
        self.saucer = None

    def launch_missile(self):
        enemy = self.saucer
        if (
            self.dead
            or self.warp_remaining > 0
            or self.missile_ammo <= 0
            or self.missile_timer > 0
            or enemy is None
            or not self.visible(enemy.position, enemy.radius)
        ):
            return False
        if any(s.missile for s in self.shots):
            return False
        nose = self.ship.position + direction(self.ship.angle) * 20
        heading = direction(self.ship.angle)
        self.shots.append(
            Shot(
                nose,
                heading * 750,
                life=3.5,
                previous=nose,
                missile=True,
            )
        )
        self.missile_ammo -= 1
        self.missile_timer = 1.5
        return True

    def activate_shield(self):
        if (
            self.dead
            or self.warp_remaining > 0
            or self.shield_charges <= 0
            or self.shield_remaining > 0
        ):
            return False
        self.shield_charges -= 1
        self.shield_remaining = 25.0
        return True

    def activate_blast(self):
        if (
            self.dead
            or self.warp_remaining > 0
            or self.blast_charges <= 0
            or self.blast is not None
        ):
            return False
        origin = Vec(self.ship.position.x, self.ship.position.y)
        maximum = (
            max(
                (
                    self.camera + Vec(x * self.width / 2, y * self.height / 2) - origin
                ).length()
                for x in (-1, 1)
                for y in (-1, 1)
            )
            + 120
        )
        self.blast = RadialBlast(
            origin, Vec(self.camera.x, self.camera.y), self.width, self.height, maximum
        )
        self.blast_charges -= 1
        self.ship.invulnerable = max(self.ship.invulnerable, 1.6)
        self.shake = max(self.shake, 12)
        return True

    def choose_powerups(self, dt):
        self.missile_timer = max(0, self.missile_timer - dt)
        self.powerup_wait += dt
        nearby = sum(
            (r.position - self.ship.position).length() < r.radius + 220
            for r in self.rocks
        )
        bullet_threat = any(
            s.hostile and (s.position - self.ship.position).length() < 220
            for s in self.shots
        )
        enemy_close = (
            self.saucer is not None
            and (self.saucer.position - self.ship.position).length() < 220
        )
        if nearby or bullet_threat or enemy_close:
            self.activate_shield()
        visible_rocks = sum(self.visible(r.position, r.radius) for r in self.rocks)
        if (
            nearby >= 3
            or (enemy_close and nearby >= 2)
            or (self.powerup_wait > 8 and visible_rocks >= 12)
        ):
            self.activate_blast()
        self.launch_missile()

    def update_blast(self, dt):
        wave = self.blast
        if wave is None:
            return
        wave.life -= dt
        wave.radius = min(wave.maximum, wave.radius + wave.maximum * dt / 1.25)
        for rock in list(self.rocks):
            if (
                self.visible(
                    rock.position, rock.radius, wave.camera, wave.width, wave.height
                )
                and (rock.position - wave.position).length()
                <= wave.radius + rock.radius
            ):
                self.rocks.remove(rock)
                self.score += POINTS[rock.tier]
                self.rocks_hit += 1
                self.kills += 1
                self.emit(rock.position, 8)
        enemy = self.saucer
        if (
            enemy
            and self.visible(
                enemy.position, enemy.radius, wave.camera, wave.width, wave.height
            )
            and (enemy.position - wave.position).length() <= wave.radius + enemy.radius
        ):
            self.destroy_enemy()
        self.shots = [
            shot
            for shot in self.shots
            if not (
                shot.hostile
                and self.visible(shot.position, 0, wave.camera, wave.width, wave.height)
                and (shot.position - wave.position).length() <= wave.radius
            )
        ]
        if wave.life <= 0:
            self.blast = None

    def next_fleet_kind(self):
        # Shuffle groups of three so repeated short flights still show variety.
        if not self.fleet_bag:
            self.fleet_bag = list(FLEET_COLORS)
            self.rng.shuffle(self.fleet_bag)
        return self.fleet_bag.pop()

    def update_saucer(self, dt):
        self.saucer_timer -= dt
        if self.saucer is None and self.saucer_timer <= 0 and not self.dead:
            side = self.rng.choice([-1, 1])
            self.saucer = Saucer(
                self.camera
                + Vec(
                    side * (self.width / 2 + 110),
                    self.rng.uniform(-self.height * 0.35, self.height * 0.35),
                ),
                self.ship.velocity * 0.55 + Vec(-side * 190, self.rng.uniform(-35, 35)),
                self.rng.random() < 0.4,
                kind=self.zone_fleet,
            )
            self.saucer_timer = self.rng.uniform(4, 7)
        if self.saucer is None:
            return
        saucer = self.saucer
        saucer.position = saucer.position + saucer.velocity * dt
        saucer.life -= dt
        saucer.cooldown -= dt
        if saucer.cooldown <= 0 and not self.dead:
            heading = math.atan2(
                self.ship.position.y - saucer.position.y,
                self.ship.position.x - saucer.position.x,
            )
            heading += (
                self.rng.uniform(-0.12, 0.12)
                if saucer.small
                else self.rng.uniform(-0.65, 0.65)
            )
            self.shots.append(
                Shot(
                    Vec(saucer.position.x, saucer.position.y),
                    direction(heading) * 410,
                    2.8,
                    True,
                    Vec(saucer.position.x, saucer.position.y),
                    FLEET_COLORS[saucer.kind],
                )
            )
            saucer.cooldown = 0.85 if saucer.small else 1.5
        if saucer.life <= 0:
            self.saucer = None

    def step(self, dt):
        if dt <= 0:
            return
        self.time += dt
        self.part_flash = max(0, self.part_flash - dt)
        self.zone_flash = max(0, self.zone_flash - dt)
        if self.warp_remaining > 0:
            self.update_warp(dt)
            return
        self.shake = max(0, self.shake - 55 * dt)
        self.fire_timer = max(0, self.fire_timer - dt)
        self.ship.invulnerable = max(0, self.ship.invulnerable - dt)
        if self.dead:
            self.restart_timer -= dt
            if self.restart_timer <= 0:
                self.session += 1
                self.reset()
                return
        else:
            self.autopilot(dt)
            self.choose_powerups(dt)
            self.update_blast(dt)
            if self.ship.thrust:
                self.ship.velocity = self.ship.velocity + direction(self.ship.angle) * (
                    195.5 * dt
                )
                if self.ship.velocity.length() > 297.5:
                    self.ship.velocity = self.ship.velocity.unit() * 297.5
                self.exhaust_timer -= dt
                if self.exhaust_timer <= 0:
                    forward = direction(self.ship.angle)
                    normal = Vec(-forward.y, forward.x)
                    for side in [-1, 1]:
                        self.emit(
                            self.ship.position - forward * 22 + normal * (side * 10.5),
                            1,
                            "exhaust",
                            self.ship.velocity - forward * 180,
                        )
                    self.exhaust_timer = 0.018
            previous = self.ship.position
            self.ship.position = self.ship.position + self.ship.velocity * dt
            self.total_distance += (self.ship.position - previous).length()
        if not self.dead:
            self.collect_parts(dt, previous)
            if self.warp_remaining > 0:
                return
            self.core_spawn_timer -= dt
            self.power_spawn_timer -= dt
            self.shield_remaining = max(0, self.shield_remaining - dt)
            if self.power_spawn_timer <= 0:
                if len(self.parts) < 4:
                    self.spawn_pickup(
                        self.part_rng.choices(
                            ["missile", "shield", "blast"], [45, 45, 10]
                        )[0]
                    )
                self.power_spawn_timer = self.part_rng.uniform(35, 55)
            self.part_timer -= dt
            if self.part_timer <= 0:
                self.replenish_parts()
                self.part_timer = 1.0
        for rock in self.rocks:
            rock.position = rock.position + rock.velocity * dt
            rock.angle += rock.spin * dt
            if (
                not self.dead
                and segment_hit(
                    self.ship.position,
                    self.ship.position,
                    rock.position,
                    rock.radius * 0.84 + 10,
                )
                is not None
            ):
                self.destroy_ship()
        self.update_saucer(dt)
        if (
            self.saucer
            and not self.dead
            and (self.saucer.position - self.ship.position).length()
            < self.saucer.radius + 10
        ):
            self.destroy_ship()
        for shot in list(self.shots):
            if shot.missile and self.saucer:
                desired = (self.saucer.position - shot.position).unit() * 850
                shot.velocity = shot.velocity + (desired - shot.velocity) * min(
                    1, dt * 4
                )
            shot.previous = shot.position
            shot.position = shot.position + shot.velocity * dt
            shot.life -= dt
            if shot.missile:
                enemy = self.saucer
                if (
                    enemy
                    and segment_hit(
                        shot.previous, shot.position, enemy.position, enemy.radius
                    )
                    is not None
                ):
                    self.destroy_enemy()
                    shot.life = 0
                # Missiles pass through all asteroids and never collide with them.
            elif shot.hostile:
                if (
                    not self.dead
                    and segment_hit(
                        shot.previous, shot.position, self.ship.position, 12
                    )
                    is not None
                ):
                    self.destroy_ship()
                    shot.life = 0
                elif shot.life > 0:
                    hits = [
                        (t, rock)
                        for rock in self.rocks
                        if (
                            t := segment_hit(
                                shot.previous,
                                shot.position,
                                rock.position,
                                rock.radius * 0.88 + 2,
                            )
                        )
                        is not None
                    ]
                    if hits:
                        self.split_rock(min(hits, key=lambda h: h[0])[1], award=False)
                        shot.life = 0
            else:
                hits = []
                for rock in self.rocks:
                    t = segment_hit(
                        shot.previous,
                        shot.position,
                        rock.position,
                        rock.radius * 0.88 + 2,
                    )
                    if t is not None:
                        hits.append((t, rock))
                saucer = self.saucer
                st = (
                    segment_hit(
                        shot.previous, shot.position, saucer.position, saucer.radius
                    )
                    if saucer
                    else None
                )
                if st is not None and (not hits or st < min(h[0] for h in hits)):
                    self.destroy_enemy()
                    shot.life = 0
                elif hits:
                    self.split_rock(min(hits, key=lambda h: h[0])[1])
                    shot.life = 0
        self.shots = [s for s in self.shots if s.life > 0][-32:]
        for spark in self.sparks:
            spark.position = spark.position + spark.velocity * dt
            spark.velocity = spark.velocity * math.exp(-1.4 * dt)
            spark.life -= dt
        self.sparks = [p for p in self.sparks if p.life > 0][-MAX_PARTICLES:]
        self.update_camera(dt)
        self.stream_timer -= dt
        if self.stream_timer <= 0:
            self.stream()
            self.stream_timer = 0.35

    def update_camera(self, dt):
        """Let movement lead the camera, with a bounded, speed-dependent offset."""
        velocity = Vec() if self.dead else self.ship.velocity
        desired = self.ship.position - velocity * CAMERA_TRAIL_SECONDS
        alpha = -math.expm1(-CAMERA_FOLLOW_RATE * max(0, dt))
        self.camera = self.camera + (desired - self.camera) * alpha
        # A radial bound preserves the travel bearing on portrait and ultrawide
        # displays, and keeps the ship visible after a resize or teleport.
        offset = self.ship.position - self.camera
        limit = min(self.width, self.height) * CAMERA_ROAM_FRACTION
        if offset.length() > limit:
            self.camera = self.ship.position - offset.unit() * limit

    def advance(self, dt):
        remaining = min(max(0, dt), 0.25)
        while remaining > 1e-9:
            step = min(remaining, 1 / 120)
            self.step(step)
            remaining -= step
