#!/usr/bin/env python3
"""Fail-closed static contract for persistent NERV beacon sieges."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def gate(name: str, condition: bool, detail: str) -> None:
    if condition:
        print(f"[PASS] {name}: {detail}")
    else:
        print(f"[FAIL] {name}: {detail}")
        ERRORS.append(name)


saved = text("src/main/java/com/projectseele/world/AngelSiegeSavedData.java")
director = text("src/main/java/com/projectseele/event/AngelSiegeDirector.java")
interface = text("src/main/java/com/projectseele/entity/SiegeAnchorAware.java")
entities = {
    name: text(f"src/main/java/com/projectseele/entity/{name}Entity.java")
    for name in ("Sachiel", "Shamshel", "Zeruel")
}
doc = text("docs/ANGEL_SIEGE_TEST.md")
commands = text("src/main/java/com/projectseele/visual/ThirdTokyoCommands.java")
telemetry = text("src/main/java/com/projectseele/world/NervCommandTelemetry.java")
lang_en = text("src/main/resources/assets/projectseele/lang/en_us.json")
lang_zh = text("src/main/resources/assets/projectseele/lang/zh_cn.json")

required_saved = (
    'DATA_VERSION = 1', '"Beacon"', '"Event"', '"Owner"',
    '"StartedAt"', '"NextWave"', '"Integrity"', '"Spawned"',
    'List.copyOf(this.sieges.values())', 'this.setDirty()'
)
gate(
    "siege.versioned_saved_data",
    all(token in saved for token in required_saved),
    "event, owner, clock, wave, integrity and entity UUIDs survive restart",
)

gate(
    "siege.no_transient_active_list",
    "static final List<Siege> ACTIVE" not in director
    and "AngelSiegeSavedData.get(level).sieges()" in director,
    "server tick is sourced from per-dimension SavedData",
)

wave_match = re.search(r"WAVE_TICKS\s*=\s*\{([^}]+)\}", director)
waves = [int(value) for value in re.findall(r"\d+", wave_match.group(1))] if wave_match else []
gate("siege.wave_schedule", waves == [100, 600, 1100], f"ticks={waves}")

gate(
    "siege.finite_route_tickets",
    "for (int step = 1; step <= 7; step++)" in director
    and "ForgeChunkManager.forceChunk" in director
    and "true, true" in director
    and "false, true" in director,
    "beacon plus three seven-step routes are acquired and released",
)

anchor_ok = "void setSiegeBeacon(BlockPos beacon)" in interface
for source in entities.values():
    anchor_ok = anchor_ok and "SiegeAnchorAware" in source
    anchor_ok = anchor_ok and 'tag.putLong("SiegeBeacon"' in source
    anchor_ok = anchor_ok and 'tag.getLong("SiegeBeacon")' in source
gate(
    "siege.persistent_angel_anchor",
    anchor_ok,
    "Sachiel, Shamshel and Zeruel retain the beacon through entity NBT",
)

gate(
    "siege.actual_beacon_threat",
    "BEACON_MAX_INTEGRITY = 1200" in director
    and "damage += 45" in director
    and "damage += 30" in director
    and "damage += 75" in director
    and "level.destroyBlock(siege.beacon(), false)" in director,
    "1200 integrity and per-Angel structural attacks can fail the operation",
)

gate(
    "siege.offline_reward",
    "new ItemEntity" in director
    and "S2_ENGINE_FRAGMENT" in director
    and "getPlayer(siege.owner())" in director,
    "offline owner reward drops at the defended beacon",
)

gate(
    "siege.cleanup",
    "data.remove(siege.beacon())" in director
    and director.count("releaseTickets(level, siege)") >= 3,
    "complete, failure and level unload release persistent state/tickets",
)

gate(
    "siege.documented_balance",
    all(token in doc for token in ("1200", "45/秒", "30/秒", "75/秒", "S² 机关碎片 ×3")),
    "new structure-only numbers are explicit for player approval",
)

gate(
    "siege.operator_commands",
    'literal("siege")' in commands
    and 'literal("status")' in commands
    and 'literal("abort")' in commands
    and "AngelSiegeDirector.status" in commands
    and "AngelSiegeDirector.abort" in commands,
    "/seele siege status and abort are wired to persistent event state",
)

gate(
    "siege.command_room_telemetry",
    "NERV BEACON: WAVE" in telemetry
    and "siege.integrity()" in telemetry
    and "siege.aliveAngels()" in telemetry,
    "strategic display reports wave, structural integrity and live hostiles",
)

gate(
    "siege.localized_abort",
    '"message.projectseele.siege_aborted"' in lang_en
    and '"message.projectseele.siege_aborted"' in lang_zh,
    "operator abort feedback is present in both bundled languages",
)

if ERRORS:
    print(f"Angel siege contract: FAIL ({len(ERRORS)} gate(s))")
    sys.exit(1)
print("Angel siege contract: PASS")