"""Fast answers to "what should I build first?" and "what should I do next?".

These questions used to go through the interactive MCP planner, which reads
the battlefield with tools and takes several model calls (9-24 s on the local
2B model).  The next step is almost always decidable from the game state: place
a finished building, fix power, follow the opening build order, add harvesters,
build an army, scout, then attack.  :func:`next_step` decides it without any
model call and returns one short spoken sentence plus the commands for a card.
Open questions that are not a plain "what next?" get a single model call with
the compact state summary from :func:`state_summary` instead (see core.py).
"""

from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass, field

from .models import GameSnapshot, ThreatAssessment
from .strategy import desired_harvester_count
from .techtree import TechTree, _article, base_type

# "What should I build first?", "what now?", "any advice?" -- a plain request for the next step.
NEXT_STEP_PATTERN = re.compile(
    r"\b(what should (?:i|we) (?:do|build|make|train|get|queue|focus on|work on)"
    r"|what (?:do|can) (?:i|we) (?:do|build)|what(?: is| s)? next|what now|next (?:move|step|priority)"
    r"|(?:any|some|give me) (?:advice|suggestions?|ideas|tips?)|what (?:\w+ )?(?:do|would) you (?:suggest|recommend)"
    r"|(?:what|which) (?:\w+ )?(?:should|shall) (?:i|we) (?:build|train|make|get|do)"
    r"|what would you (?:do|build)|suggest (?:something|a move|what)|recommend (?:something|a move)|help me"
    r"|where (?:do|should) (?:i|we) start|how (?:do|should) (?:i|we) start)\b"
)
BUILD_FOCUS = re.compile(r"\b(build|make|construct|queue|first)\b")

# Opening order by role: power, then the economy, then the two production buildings.
OPENING = ("power", "refinery", "barracks", "factory")
CLASSIC_ROLES = {
    "powr": "power", "apwr": "power", "gapowr": "power", "napowr": "power",
    "proc": "refinery", "garefn": "refinery", "narefn": "refinery",
    "tent": "barracks", "barr": "barracks", "gapile": "barracks", "nahand": "barracks",
    "weap": "factory", "gaweap": "factory", "naweap": "factory",
    "dome": "radar", "naradr": "radar",
}
NAME_ROLES = (
    ("power", ("power plant", "reactor", "power station")),
    ("refinery", ("refinery",)),
    ("barracks", ("barracks",)),
    ("factory", ("war factory", "vehicle factory")),
    ("radar", ("radar",)),
)
NON_COMBAT = frozenset({"harv", "cmin", "mcv", "amcv", "smcv"})
# The engine takes at most 12 orders in one request (CompanionBridge MaxCommandsPerRequest).
MAX_ORDERS = 12
# An army worth sending: at least 8 fighters together worth 7,000 credits (about seven tanks and some infantry).
WAVE_UNITS, WAVE_VALUE = 8, 7000


@dataclass
class Advice:
    text: str
    summary: str = ""
    commands: list[dict] = field(default_factory=list)
    key: str = ""


def is_next_step_question(text: str) -> bool:
    return bool(NEXT_STEP_PATTERN.search(" ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())))


class Advisor:
    def __init__(self, snapshot: GameSnapshot, threat: ThreatAssessment | None = None) -> None:
        self.snapshot = snapshot
        self.threat = threat or ThreatAssessment()
        self.tree = TechTree(snapshot)
        self.available = [item.lower() for item in snapshot.available_production]

    # -- naming and roles --------------------------------------------------------------
    def name(self, item: str) -> str:
        return self.tree.name(item) if self.tree.factions else self.snapshot.actor_name(item)

    def plural(self, item: str) -> str:
        name = self.name(item)
        if name.lower().endswith(("infantry", "team", "section")) or name.endswith("s"):
            return name
        if name.endswith("man"):
            return name[:-3] + "men"
        return name + "s"

    def roles(self, kind: str) -> set[str]:
        kind = base_type(kind)
        roles: set[str] = set()
        entry = self.tree.items.get(kind)
        if entry is not None:
            provides, produces = set(entry.get("provides", ())), set(entry.get("produces", ()))
            if "power" in provides:
                roles.add("power")
            if "refinery" in provides:
                roles.add("refinery")
            if "infantry" in produces:
                roles.add("barracks")
            if "vehicle" in produces:
                roles.add("factory")
            if "radar" in provides:
                roles.add("radar")
            return roles
        if kind in CLASSIC_ROLES:
            return {CLASSIC_ROLES[kind]}
        name = self.snapshot.actor_name(kind).lower()
        return {role for role, words in NAME_ROLES if any(word in name for word in words)}

    def owned_roles(self) -> set[str]:
        return {role for building in self.snapshot.buildings for role in self.roles(building.kind)}

    def queued(self) -> list[dict]:
        return list(self.snapshot.production)

    @staticmethod
    def finished(entry: dict) -> bool:
        return float(entry.get("progress", 0)) >= 0.999 or int(entry.get("remaining_ticks", 1)) <= 0

    def _is_structure(self, entry: dict) -> bool:
        queue = str(entry.get("queue_type", "")).lower()
        if queue in {"building", "defense", "support"}:
            return True
        item = base_type(str(entry.get("item", "")))
        return not queue and (self.tree.items.get(item, {}).get("kind") == "building" or bool(self.roles(item)))

    def queued_roles(self) -> set[str]:
        return {role for entry in self.queued() for role in self.roles(str(entry.get("item", "")))}

    def available_for(self, role: str) -> str | None:
        candidates = [item for item in self.available if role in self.roles(item) and not item.endswith("f")]
        if not candidates:
            return None
        order = {item: index for index, item in enumerate(self.available)}
        return min(candidates, key=lambda item: (self.tree.items.get(base_type(item), {}).get("order", 0), order[item]))

    def basic_unit(self, queue: str, word: str) -> str | None:
        """The faction's standard rifleman ("Infantry") or battle tank ("Vehicle") when buildable now."""
        for item in self.available:
            entry = self.tree.items.get(base_type(item), {})
            name = self.name(item).lower()
            if self.tree.known and entry.get("queue") != queue:
                continue
            if word == "tank" and "tank" in name:
                return item
            if word == "infantry" and not any(skip in name for skip in ("engineer", "dog", "spy", "medic", "technician")) and (
                entry.get("cost", 0) <= 400 or base_type(item) in {"e1", "e2"}
            ):
                return item
        return None

    # -- the decision -------------------------------------------------------------------
    def next_step(self, *, build_focus: bool = False) -> Advice | None:
        snapshot = self.snapshot
        if snapshot.done:
            return Advice(f"The match is over ({snapshot.result or 'finished'}); there is nothing left to do.", key="done")
        units = [unit for unit in snapshot.units if "husk" not in unit.kind.lower()]
        mcv = next((unit for unit in units if base_type(unit.kind) in {"mcv", "amcv", "smcv"}
                    or "construction vehicle" in snapshot.actor_name(unit.kind).lower()), None)
        if mcv is not None and not snapshot.buildings:
            return Advice(
                f"Deploy your {self.name(mcv.kind)} first; nothing can be built until the Construction Yard is up.",
                f"Deploy the {self.name(mcv.kind)}",
                [{"action": "deploy", "actor_id": mcv.actor_id}],
                "deploy",
            )
        ready = next((entry for entry in self.queued() if self.finished(entry) and self._is_structure(entry)), None)
        if ready is not None:
            item = str(ready.get("item", "")).lower()
            # A defence goes on the side of the base the enemy comes from; anything else wherever the engine finds room.
            at = front_cell(snapshot, len(self.defences())) if self.is_defence(item) else None
            command = {"action": "place_building", "item_type": item}
            if at is not None:
                command.update(target_x=at[0], target_y=at[1])
            return Advice(
                f"Place the finished {self.name(item)} first; the build queue waits until it's down.",
                f"Place the {self.name(item)}",
                [command],
                "place",
            )
        if not build_focus:
            defend = self._defend()
            if defend is not None:
                return defend
        power = self._power() or self._power_margin()
        if power is not None:
            return power
        opening = self._opening()
        if opening is not None:
            return opening
        economy = self._harvester()
        if economy is not None:
            return economy
        rally = self._rally()
        if rally is not None:
            return rally
        owned = self.owned_roles()
        # The enemy's first raids come at about minute 4: two defences on the side of the base it comes from.
        defence = self.defence_item()
        if defence and "factory" in owned and len(self.defences()) < 2 and not self.defence_queued():
            return Advice(
                f"Build {_article(self.name(defence))}: it guards the side of the base the enemy comes from while your army grows.",
                f"Build {_article(self.name(defence))}",
                [{"action": "build", "item_type": defence}],
                "build:defence",
            )
        if "radar" not in owned and "radar" not in self.queued_roles():
            radar = self.available_for("radar")
            if radar:
                return Advice(
                    f"Build {_article(self.name(radar))} next: it lights up the minimap and unlocks advanced units.",
                    f"Build {_article(self.name(radar))}",
                    [{"action": "build", "item_type": radar}],
                    "build:radar",
                )
        if self.count("refinery") < 2 and "refinery" not in self.queued_roles():
            refinery = self.available_for("refinery")
            if refinery:
                return Advice(
                    f"Build a second {self.name(refinery)}: it comes with another harvester, and one refinery can't pay "
                    "for a factory that never stops.",
                    f"Build {_article(self.name(refinery))}",
                    [{"action": "build", "item_type": refinery}],
                    "build:refinery",
                )
        return self._army(build_focus=build_focus)

    # -- defences, rally points ---------------------------------------------------------
    def is_defence(self, kind: str) -> bool:
        return is_basic_defence(self.tree.items.get(base_type(kind)))

    def defences(self) -> list:
        return [building for building in self.snapshot.buildings if self.is_defence(building.kind)]

    def defence_item(self) -> str | None:
        items = [item for item in self.available if self.is_defence(item)]
        return min(items, key=lambda item: self.tree.items.get(base_type(item), {}).get("cost", 0), default=None)

    def defence_queued(self) -> bool:
        return any(self.is_defence(str(entry.get("item", ""))) for entry in self.queued())

    def count(self, role: str) -> int:
        return sum(1 for building in self.snapshot.buildings if role in self.roles(building.kind))

    def cost(self, kind: str) -> int:
        return int(self.tree.items.get(base_type(kind), {}).get("cost", 0))

    def _rally(self) -> Advice | None:
        """New units gather on the side of the base the enemy comes from, not at the doors (a crowd there blocks the
        factory). Only where the engine says where the rally point is: one at the door (within 6 cells) is the default."""
        if "factory" not in self.owned_roles():
            return None
        staging = front_cell(self.snapshot, 0, 5)
        if staging is None:
            return None
        doors = [building for building in self.snapshot.buildings
                 if ("barracks" in self.roles(building.kind) or "factory" in self.roles(building.kind))
                 and building.rally_x >= 0
                 and (building.rally_x - building.cell_x) ** 2 + (building.rally_y - building.cell_y) ** 2 <= 6 ** 2
                 and (building.rally_x - staging[0]) ** 2 + (building.rally_y - staging[1]) ** 2 > 2 ** 2][:MAX_ORDERS]
        if not doors:
            return None
        names = " and ".join(dict.fromkeys(self.name(building.kind) for building in doors))
        return Advice(
            f"Set the rally point of your {names} toward the enemy, so new units gather at the front instead of crowding the doors.",
            f"Set {len(doors)} rally point{'s' if len(doors) != 1 else ''} toward the enemy",
            [{"action": "set_rally_point", "actor_id": building.actor_id, "target_x": staging[0], "target_y": staging[1]}
             for building in doors],
            "rally",
        )

    def _defend(self) -> Advice | None:
        snapshot = self.snapshot
        if not (self.threat.heated and snapshot.visible_enemies):
            return None
        units = [unit for unit in snapshot.units if "husk" not in unit.kind.lower()]
        assets = snapshot.buildings or units

        def proximity(enemy) -> int:
            return min(((enemy.cell_x - asset.cell_x) ** 2 + (enemy.cell_y - asset.cell_y) ** 2 for asset in assets), default=0)

        contact = min(snapshot.visible_enemies, key=proximity)
        defenders = sorted((unit for unit in units if unit.idle and unit.can_attack and base_type(unit.kind) not in NON_COMBAT),
                           key=lambda unit: (unit.cell_x - contact.cell_x) ** 2 + (unit.cell_y - contact.cell_y) ** 2)[:MAX_ORDERS]
        # Revealed maps can expose a large army on a distant coast: only enemies near the base call for defenders.
        if not defenders or proximity(contact) > 20 ** 2:
            return None
        count = len(defenders)
        return Advice(
            f"Enemies are at your base; send your {count} idle fighter{'s' if count != 1 else ''} at them now.",
            f"Attack-move {count} idle unit{'s' if count != 1 else ''} to the attackers",
            [{"action": "attack_move", "actor_id": unit.actor_id, "target_x": contact.cell_x, "target_y": contact.cell_y}
             for unit in defenders],
            "defend",
        )

    def _power(self) -> Advice | None:
        snapshot = self.snapshot
        if not snapshot.buildings or snapshot.power_drained <= snapshot.power_provided:
            return None
        if "power" in self.queued_roles():
            return None
        item = self.available_for("power")
        if item is None:
            return None
        short = snapshot.power_drained - snapshot.power_provided
        return Advice(
            f"Power is short by {short}; build another {self.name(item)} so production runs at full speed.",
            f"Build {_article(self.name(item))}",
            [{"action": "build", "item_type": item}],
            "build:power",
        )

    def _power_margin(self) -> Advice | None:
        """Low power makes everything three times slower: a new plant before the next building uses the last of it."""
        snapshot, owned = self.snapshot, self.owned_roles()
        left = snapshot.power_provided - snapshot.power_drained
        if "power" not in owned or "factory" not in owned or left >= 50 or "power" in self.queued_roles():
            return None
        item = self.available_for("power")
        if item is None:
            return None
        return Advice(
            f"Power is almost used up ({left} left); build another {self.name(item)} before the next building.",
            f"Build {_article(self.name(item))}",
            [{"action": "build", "item_type": item}],
            "build:power",
        )

    def _opening(self) -> Advice | None:
        owned, queued = self.owned_roles(), self.queued_roles()
        for role in OPENING:
            if role in owned or role in queued:
                continue
            item = self.available_for(role)
            if item is None:
                continue
            name = self.name(item)
            reason = {
                "power": self._power_reason(),
                "refinery": "it comes with a harvester and pays for everything else",
                "barracks": self._barracks_reason(),
                "factory": self._factory_reason(),
            }[role]
            first = role == "power" and not owned and not self.snapshot.production
            text = f"{'Start with' if first else 'Build'} {_article(name)}{'' if first else ' next'}: {reason}."
            return Advice(text, f"Build {_article(name)}", [{"action": "build", "item_type": item}], f"build:{role}")
        return None

    def _power_reason(self) -> str:
        dependants = [self.name(item) for item in self._role_items("barracks")[:1] + self._role_items("refinery")[:1]]
        if len(dependants) == 2:
            return f"the {dependants[0]} and the {dependants[1]} both need it"
        return "everything else needs power"

    def _barracks_reason(self) -> str:
        infantry = self._roster_basic("Infantry", "infantry")
        return f"you can train {self.plural(infantry)}" if infantry else "it trains your infantry"

    def _factory_reason(self) -> str:
        tank = self._roster_basic("Vehicle", "tank")
        return f"it builds {self.plural(tank)}" if tank else "it builds your vehicles"

    def _role_items(self, role: str) -> list[str]:
        if self.tree.known:
            return [item for item in sorted(self.tree.items, key=lambda item: self.tree.items[item].get("order", 0))
                    if role in self.roles(item)]
        return [item for item in self.available if role in self.roles(item)]

    def _roster_basic(self, queue: str, word: str) -> str | None:
        if not self.tree.known:
            return None
        for item, entry in sorted(self.tree.items.items(), key=lambda pair: pair[1].get("order", 0)):
            name = entry["name"].lower()
            if entry.get("queue") != queue:
                continue
            if word == "tank" and "tank" in name:
                return item
            if word == "infantry" and entry.get("cost", 0) <= 400 and not any(
                    skip in name for skip in ("engineer", "dog", "spy", "medic", "technician")):
                return item
        return None

    def _harvester(self) -> Advice | None:
        snapshot = self.snapshot
        if "refinery" not in self.owned_roles():
            return None
        target = desired_harvester_count(snapshot)
        if snapshot.harvester_count >= target:
            return None
        harvesters = [item for item in self.available if base_type(item) in {"harv", "cmin"}
                      or any(word in self.name(item).lower() for word in ("harvester", "miner", "ore truck"))]
        if not harvesters or any(base_type(str(entry.get("item", ""))) == base_type(harvesters[0]) for entry in self.queued()):
            return None
        item = harvesters[0]
        return Advice(
            f"Train another {self.name(item)}: you have {snapshot.harvester_count} and this map supports {target}.",
            f"Train 1 {self.name(item)}",
            [{"action": "train", "item_type": item}],
            "train:harvester",
        )

    def _army(self, *, build_focus: bool) -> Advice | None:
        snapshot = self.snapshot
        fighters = [unit for unit in snapshot.units if unit.can_attack and "husk" not in unit.kind.lower()
                    and base_type(unit.kind) not in {"harv", "cmin", "mcv", "amcv", "smcv"}]
        busy = {str(entry.get("queue_type", "")).lower() for entry in self.queued()}
        tank = self.basic_unit("Vehicle", "tank")
        infantry = self.basic_unit("Infantry", "infantry")
        if tank and "vehicle" not in busy:
            return Advice(
                f"Build up the army: train {self.plural(tank)}; you have {len(fighters)} combat unit{'s' if len(fighters) != 1 else ''}.",
                f"Train 3 {self.plural(tank)}",
                [{"action": "train", "item_type": tank} for _ in range(3)],
                "train:tank",
            )
        if infantry and "infantry" not in busy and (len(fighters) < 8 or snapshot.cash >= 1500):
            return Advice(
                f"Train more {self.plural(infantry)} to protect the base while it grows.",
                f"Train 3 {self.plural(infantry)}",
                [{"action": "train", "item_type": infantry} for _ in range(3)],
                "train:infantry",
            )
        # Money piling up: a second factory makes tanks faster; more defences hold the base while the army is away.
        if snapshot.cash >= 3000 and self.count("factory") < 2 and "factory" not in self.queued_roles():
            factory = self.available_for("factory")
            if factory:
                return Advice(
                    f"You have {snapshot.cash} credits unspent; a second {self.name(factory)} builds tanks faster.",
                    f"Build {_article(self.name(factory))}",
                    [{"action": "build", "item_type": factory}],
                    "build:factory",
                )
        defence = self.defence_item()
        if defence and snapshot.cash >= 2500 and len(self.defences()) < 4 and not self.defence_queued():
            return Advice(
                f"You have {snapshot.cash} credits unspent; another {self.name(defence)} holds the base while the army is away.",
                f"Build {_article(self.name(defence))}",
                [{"action": "build", "item_type": defence}],
                "build:defence",
            )
        if build_focus:
            return None
        if fighters and not snapshot.visible_enemy_buildings and not snapshot.remembered_enemy_buildings:
            # Looking for the enemy base is an order like any other: one cheap scout, or, once there is an army of 12, the
            # fighters together. One order at a time: while any fighter is busy (out looking, or fighting), nobody
            # new is sent.
            # A ready army (12 idle fighters worth 7,000 credits) searches whatever a few others are doing; a single
            # scout only goes when nobody is out.
            waiting = [unit for unit in fighters if unit.idle]
            army = len(waiting) >= 12 and sum(self.cost(unit.kind) for unit in waiting) >= WAVE_VALUE
            if not army and len(waiting) < len(fighters):
                return None
            centre = (sum(unit.cell_x for unit in waiting) / len(waiting), sum(unit.cell_y for unit in waiting) / len(waiting))
            # Enemy units in sight away from the base (a harvester on its way home, a raiding party): the army goes
            # after the nearest of them; they lead to the rest.
            sighted = min((enemy for enemy in snapshot.visible_enemies if land_reachable(snapshot, enemy.cell_x, enemy.cell_y)),
                          key=lambda enemy: (enemy.cell_x - centre[0]) ** 2 + (enemy.cell_y - centre[1]) ** 2, default=None)
            if army and sighted is not None:
                group = sorted(waiting, key=lambda unit: unit.actor_id)[:MAX_ORDERS]
                return Advice(
                    f"We haven't found the enemy base yet, but there is an enemy {self.name(sighted.kind)} in sight; advance {len(group)} units toward it.",
                    f"Advance {len(group)} units toward the enemy {self.name(sighted.kind)}",
                    [{"action": "attack_move", "actor_id": unit.actor_id, "target_x": sighted.cell_x, "target_y": sighted.cell_y}
                     for unit in group],
                    "hunt",
                )
            goal = search_goal(snapshot, centre)
            if goal and army:
                group = sorted(waiting, key=lambda unit: unit.actor_id)[:MAX_ORDERS]
                return Advice(
                    f"We haven't found the enemy base yet; advance {len(group)} units together across the map to find it.",
                    f"Advance {len(group)} units to find the enemy base",
                    [{"action": "attack_move", "actor_id": unit.actor_id, "target_x": goal[0], "target_y": goal[1]}
                     for unit in group],
                    "sweep",
                )
            if goal:
                def price(unit) -> int:
                    return int(self.tree.items.get(base_type(unit.kind), {}).get("cost", 99999))
                scout = min(fighters, key=lambda unit: (price(unit), -unit.speed, unit.actor_id))
                return Advice(
                    f"We haven't found the enemy base yet; send your {self.name(scout.kind)} to scout the far side of the map.",
                    f"Send the {self.name(scout.kind)} to scout",
                    [{"action": "move", "actor_id": scout.actor_id, "target_x": goal[0], "target_y": goal[1]}],
                    "scout",
                )
            return Advice(
                f"We haven't found the enemy base yet; send a scout to explore the {100 - round(snapshot.explored_percent)}% of the map still in fog.",
                key="scout",
            )
        targets = snapshot.visible_enemy_buildings or snapshot.remembered_enemy_buildings
        if not targets:
            return None

        def nearest(group):
            """The enemy building nearest to a group, leaving out any the group already stands on (a remembered
            building that is gone, or one they have reached): the same order again would change nothing."""
            cx = sum(unit.cell_x for unit in group) / len(group)
            cy = sum(unit.cell_y for unit in group) / len(group)
            return min((target for target in targets if (target.cell_x - cx) ** 2 + (target.cell_y - cy) ** 2 > 4 ** 2),
                       key=lambda target: (target.cell_x - cx) ** 2 + (target.cell_y - cy) ** 2, default=None)

        # Fighters standing idle inside the enemy base: an attack-move does not make them shoot buildings, so they attack
        # the nearest building they can see, all together; with none in sight, they go on to the next one remembered.
        inside = [unit for unit in fighters if unit.idle and any(
            (unit.cell_x - target.cell_x) ** 2 + (unit.cell_y - target.cell_y) ** 2 <= 14 ** 2 for target in targets)]
        pressing = inside[:MAX_ORDERS]
        if pressing and snapshot.visible_enemy_buildings:
            cx = sum(unit.cell_x for unit in pressing) / len(pressing)
            cy = sum(unit.cell_y for unit in pressing) / len(pressing)
            building = min(snapshot.visible_enemy_buildings,
                           key=lambda target: (target.cell_x - cx) ** 2 + (target.cell_y - cy) ** 2)
            if (building.cell_x - cx) ** 2 + (building.cell_y - cy) ** 2 <= 14 ** 2:
                n = len(pressing)
                return Advice(
                    f"Your {n} unit{' is' if n == 1 else 's are'} next to the enemy's {self.name(building.kind)}; attack it{'' if n == 1 else ' together'}.",
                    f"Attack the {self.name(building.kind)} with {n} unit{'' if n == 1 else 's'}",
                    [{"action": "attack", "actor_id": unit.actor_id, "target_actor_id": building.actor_id} for unit in pressing],
                    "press",
                )
        onward = nearest(pressing) if pressing else None
        if onward is not None:
            n = len(pressing)
            return Advice(
                f"Your {n} unit{' is' if n == 1 else 's are'} standing in the enemy base; send {'it' if n == 1 else 'them'} on to the next building.",
                f"Attack-move {n} unit{'' if n == 1 else 's'} to the next enemy building",
                [{"action": "attack_move", "actor_id": unit.actor_id, "target_x": onward.cell_x, "target_y": onward.cell_y}
                 for unit in pressing],
                "press",
            )
        # An attack is a wave: the idle fighters go together once there are 8 or more worth 7,000 credits. A smaller
        # army stays home with the defences; units already fighting are left to it. One card carries at most 12 orders
        # (the engine refuses more): the strongest 12 go first, and the rest follow on the next card while what is left
        # is still an army.
        wave = [unit for unit in fighters if unit.idle and unit not in inside]
        attackers = sorted(wave, key=lambda unit: (-self.cost(unit.kind), unit.actor_id))[:MAX_ORDERS]
        target = nearest(attackers) if attackers else None
        worth = sum(self.cost(unit.kind) for unit in wave)
        if target is not None and len(wave) >= WAVE_UNITS and worth >= WAVE_VALUE:
            return Advice(
                f"Your {len(wave)} combat units are a real army now ({worth} credits); attack-move them to the enemy base together.",
                f"Attack-move {len(attackers)} units to the enemy base",
                [{"action": "attack_move", "actor_id": unit.actor_id, "target_x": target.cell_x, "target_y": target.cell_y}
                 for unit in attackers],
                "attack",
            )
        return None


def is_basic_defence(entry: dict | None) -> bool:
    """A faction's basic ground defence (Pill Box, Sentry Gun, Gun Bunker, Guard Tower...): never a wall, AA or a
    superweapon. The browser adviser (web/src/adviser.ts isBasicDefence) decides the same."""
    if not entry:
        return False
    cost, name = int(entry.get("cost", 0) or 0), str(entry.get("name", ""))
    return (str(entry.get("queue", "")).lower() == "support" and 0 < cost <= 800
            and re.search(r"pill ?box|sentry|bunker|guard tower|autocannon", name, re.I) is not None
            and re.search(r"\bair\b|\baa\b|anti-air", name, re.I) is None)


def _round(value: float) -> int:
    """JavaScript's Math.round (halves go up), so both advisers pick the same cell."""
    return math.floor(value + 0.5)


def front_cell(snapshot: GameSnapshot, index: int, out: int = 8) -> tuple[int, int] | None:
    """Where the next defence goes: on the side of the base that faces the enemy (the known enemy building nearest to
    the base, else the far side of the map), ``out`` cells from the base's middle; each further one 3 cells to one
    side. The browser adviser (web/src/adviser.ts frontCell) decides the same."""
    own, width, height = snapshot.buildings, snapshot.map_width, snapshot.map_height
    if not own or width <= 0 or height <= 0:
        return None
    hx = sum(actor.cell_x for actor in own) / len(own)
    hy = sum(actor.cell_y for actor in own) / len(own)
    known = (*snapshot.visible_enemy_buildings, *snapshot.remembered_enemy_buildings)
    near = min(known, key=lambda actor: (actor.cell_x - hx) ** 2 + (actor.cell_y - hy) ** 2, default=None)
    dx = (near.cell_x if near else width - 1 - hx) - hx
    dy = (near.cell_y if near else height - 1 - hy) - hy
    length = math.hypot(dx, dy)
    if length < 1:
        return None
    dx, dy = dx / length, dy / length
    side = (0, 3, -3, 6, -6)[index % 5]
    return (max(0, min(width - 1, _round(hx + dx * out - dy * side))),
            max(0, min(height - 1, _round(hy + dy * out + dx * side))))


def _spatial(snapshot: GameSnapshot):
    width, height, channels = snapshot.map_width, snapshot.map_height, snapshot.spatial_channels
    if channels >= 5 and width > 0 and height > 0 and len(snapshot.spatial_map) >= width * height * channels * 4:
        return snapshot.spatial_map
    return None


def _cell(snapshot: GameSnapshot, grid: bytes, x: int, y: int, channel: int) -> float:
    return struct.unpack_from("<f", grid, ((y * snapshot.map_width + x) * snapshot.spatial_channels + channel) * 4)[0]


def land_reachable(snapshot: GameSnapshot, x: int, y: int) -> bool:
    """Whether land units can stand on a cell (the engine's grid, channel 3); True when the grid is not there."""
    grid = _spatial(snapshot)
    if grid is None or x < 0 or y < 0 or x >= snapshot.map_width or y >= snapshot.map_height:
        return True
    return _cell(snapshot, grid, x, y, 3) >= 1


def search_goal(snapshot: GameSnapshot, start: tuple[float, float] | None = None) -> tuple[int, int] | None:
    """Where to look for an enemy base nobody has seen: the far side of the map from our own base (its mirror
    through the centre), then the mirrors across each axis, then the centre; the first of them never explored. Then
    any place never explored, the farthest from our base first. Once all of it has been seen, the enemy can only be
    somewhere out of sight now: a sweep along the rows of the map (every 8 cells, back and forth), from where
    ``start`` (the army) stands on to the next place not in sight. Only cells land units can reach. None: nowhere to
    look. The browser adviser (RTSAI-WebGame web/src/adviser.ts searchGoal) decides the same."""
    width, height = snapshot.map_width, snapshot.map_height
    own = snapshot.buildings or snapshot.units
    if not own or width <= 0 or height <= 0:
        return None
    home_x = sum(actor.cell_x for actor in own) // len(own)
    home_y = sum(actor.cell_y for actor in own) // len(own)
    grid = _spatial(snapshot)

    # The engine's grid: channel 3 land passable (1), channel 4 fog (0 never seen, 0.5 seen before, 1 in sight now).
    def explored(x: int, y: int) -> bool:
        return grid is not None and _cell(snapshot, grid, x, y, 4) >= 0.5

    for x, y in ((width - 1 - home_x, height - 1 - home_y), (width - 1 - home_x, home_y),
                 (home_x, height - 1 - home_y), (width // 2, height // 2)):
        x, y = max(0, min(width - 1, x)), max(0, min(height - 1, y))
        if (x - home_x) ** 2 + (y - home_y) ** 2 > 20 ** 2 and not explored(x, y) and land_reachable(snapshot, x, y):
            return x, y
    if grid is None:
        return None
    path = []
    columns = math.ceil((width - 4) / 8)
    for row, y in enumerate(range(4, height, 8)):
        for i in range(columns):
            path.append((4 + (columns - 1 - i) * 8 if row % 2 else 4 + i * 8, y))
    best, far = None, 20 ** 2
    for x, y in path:
        distance = (x - home_x) ** 2 + (y - home_y) ** 2
        if distance > far and not explored(x, y) and land_reachable(snapshot, x, y):
            best, far = (x, y), distance
    if best is not None or start is None or not path:
        return best
    sx, sy = start
    first = min(range(len(path)), key=lambda i: (path[i][0] - sx) ** 2 + (path[i][1] - sy) ** 2)
    for j in range(1, len(path) + 1):
        x, y = path[(first + j) % len(path)]
        if _cell(snapshot, grid, x, y, 4) < 1 and land_reachable(snapshot, x, y) and (x - sx) ** 2 + (y - sy) ** 2 >= 12 ** 2:
            return x, y
    return None


def state_summary(snapshot: GameSnapshot, threat: ThreatAssessment | None = None) -> str:
    """A compact, fog-respecting summary for one short model call (no ids, no images)."""
    from .nl_orders import vocabulary_context  # local import: nl_orders imports this package's tree

    threat = threat or ThreatAssessment()
    power = snapshot.power_provided - snapshot.power_drained
    lines = [
        vocabulary_context(snapshot),
        f"Cash: ${snapshot.cash:,}; power {power:+}; harvesters {snapshot.harvester_count}; "
        f"threat {threat.level}; explored {round(snapshot.explored_percent)}%",
    ]
    if snapshot.kills_cost or snapshot.deaths_cost:
        lines.append(f"Trades: destroyed ${snapshot.kills_cost:,}, lost ${snapshot.deaths_cost:,}")
    return "\n".join(lines)
