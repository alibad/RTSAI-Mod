"""The skirmish adviser keeps the enemy buildings it has seen after they drop out of sight (advisor.EnemyBaseMemory)."""

import base64
import struct

from openra_ai_companion.advisor import EnemyBaseMemory
from openra_ai_companion.models import GameSnapshot


def _fog(in_sight) -> str:
    grid = bytearray(20 * 20 * 5 * 4)
    for y in range(20):
        for x in range(20):
            struct.pack_into("<f", grid, ((y * 20 + x) * 5 + 4) * 4, 1.0 if in_sight(x, y) else 0.5)
    return base64.b64encode(bytes(grid)).decode()


def _snapshot(tick: int, visible: list[dict], in_sight) -> GameSnapshot:
    return GameSnapshot.from_dict({"tick": tick, "map_width": 20, "map_height": 20, "visible_enemy_buildings": visible,
                                   "spatial_map": _fog(in_sight), "spatial_channels": 5})


YARD = {"actor_id": 7, "type": "nacnst", "cell_x": 15, "cell_y": 15}


def test_a_building_seen_stays_known_until_its_cell_is_in_sight_without_it() -> None:
    memory = EnemyBaseMemory()
    memory.recall(_snapshot(100, [YARD], lambda x, y: True))
    kept = memory.recall(_snapshot(200, [], lambda x, y: False))
    assert [building.actor_id for building in kept.remembered_enemy_buildings] == [7]
    gone = memory.recall(_snapshot(300, [], lambda x, y: (x, y) == (15, 15)))
    assert gone.remembered_enemy_buildings == ()


def test_a_new_match_starts_empty() -> None:
    memory = EnemyBaseMemory()
    memory.recall(_snapshot(400, [YARD], lambda x, y: True))
    assert memory.recall(_snapshot(10, [], lambda x, y: False)).remembered_enemy_buildings == ()


def test_where_enemy_units_were_seen_is_kept_until_looked_at() -> None:
    memory = EnemyBaseMemory()
    raider = {"actor_id": 70, "type": "r2karrar", "cell_x": 12, "cell_y": 4}
    seen = GameSnapshot.from_dict({"tick": 20, "map_width": 20, "map_height": 20, "visible_enemies": [raider],
                                   "spatial_map": _fog(lambda x, y: True), "spatial_channels": 5})
    memory.recall(seen)
    assert memory.recall(_snapshot(30, [], lambda x, y: False)).enemy_trail == ((12, 4),)
    assert memory.recall(_snapshot(40, [], lambda x, y: (x, y) == (12, 4))).enemy_trail == ()
