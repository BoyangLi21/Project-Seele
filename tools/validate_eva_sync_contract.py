#!/usr/bin/env python3
"""Fail-closed static contract for persistent EVA pilot synchronization."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def gate(name: str, condition: bool, detail: str) -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {name}: {detail}")
    if not condition:
        ERRORS.append(name)


data = text("src/main/java/com/projectseele/capability/EvaPilotData.java")
capability = text("src/main/java/com/projectseele/capability/EvaPilotCapability.java")
provider = text("src/main/java/com/projectseele/capability/EvaPilotProvider.java")
common = text("src/main/java/com/projectseele/CommonEvents.java")
events = text("src/main/java/com/projectseele/GameEvents.java")
entity = text("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
config = text("src/main/java/com/projectseele/config/SeeleConfig.java")
hud = text("src/main/java/com/projectseele/client/EvaHud.java")
telemetry = text("src/main/java/com/projectseele/world/NervCommandTelemetry.java")
commands = text("src/main/java/com/projectseele/visual/PilotCommands.java")
doc = text("docs/EVA_SYNCHRONIZATION_TEST.md")
launcher = text("tools/start_test.bat")


gate(
    "sync.capability_lifecycle",
    all(token in provider for token in (
        "ICapabilitySerializable<CompoundTag>", "EvaPilotCapability.DATA",
        "serializeNBT()", "deserializeNBT(CompoundTag tag)",
    )) and "event.register(EvaPilotData.class)" in common
    and all(token in events for token in (
        "AttachCapabilitiesEvent<Entity>", "new EvaPilotProvider()",
        "PlayerEvent.Clone", "reviveCaps()", "copyFrom(oldData)",
        "invalidateCaps()",
    )),
    "player capability is registered, attached, serialized and copied across respawn",
)

gate(
    "sync.persistent_progress",
    all(token in data for token in (
        'tag.putFloat("Synchronization"', 'tag.putInt("ActiveDrivingTicks"',
        'tag.contains("Synchronization")', "tickActiveDriving()",
        "GROWTH_INTERVAL_TICKS = 20 * 60", "this.increase(driveGainPerMinute())",
    )),
    "base percentage and partial minute survive restart",
)

gate(
    "sync.configured_defaults",
    all(token in config for token in (
        'defineInRange("initial", 40.0D', 'defineInRange("maximum", 100.0D',
        'defineInRange("driveGainPerMinute", 0.25D',
        'defineInRange("angelKillGain", 2.5D',
        'defineInRange("maxMobilityBonus", 0.25D',
        'defineInRange("maxAttackSpeedBonus", 0.25D',
        'defineInRange("feedbackThreshold", 60.0D',
        'defineInRange("maxFeedbackFraction", 0.35D',
    )),
    "40 percent baseline, bounded growth and neural-feedback risk are configurable",
)

gate(
    "sync.authoritative_growth",
    "EvaPilotCapability.tickActiveDriving(pilot)" in entity
    and "EvaPilotCapability.awardAngelKill(pilot)" in events
    and "pilot.getVehicle() instanceof EvaUnit01Entity" in events
    and "msg.projectseele.sync_angel_gain" in events,
    "only active entry-plug time and the riding pilot's Angel kill advance progress",
)

gate(
    "sync.entity_replication",
    all(token in entity for token in (
        "DATA_PILOT_SYNCHRONIZATION", "getPilotSynchronization()",
        'tag.putFloat("SeelePilotSynchronization"',
        'tag.contains("SeelePilotSynchronization")',
        "tickPilotSynchronization()", "EvaPilotCapability.synchronization(pilot)",
    )),
    "the server mirrors persistent pilot progress through entity data and airframe NBT",
)

gate(
    "sync.response_scaling",
    all(token in entity for token in (
        "synchronizedCooldown(MELEE_COOLDOWN_TICKS)",
        "synchronizedCooldown(SMASH_COOLDOWN_TICKS)",
        "synchronizedCooldown(STOMP_COOLDOWN_TICKS)",
        "synchronizedCooldown(SeeleConfig.EVA_RIFLE_INTERVAL_TICKS.get())",
        "EvaPilotCapability.mobilityMultiplier(",
        "return variantSpeed * synchronizationSpeed",
    )) and "baseTicks / speed" in entity,
    "movement and selected server cooldowns improve without changing hit damage",
)

gate(
    "sync.actual_hull_feedback",
    all(token in entity for token in (
        "applyHullDamageWithFeedback", "healthBefore - this.getHealth()",
        "neuralFeedbackFraction(synchronization)", "pilot.hurt(source, feedback)",
        "msg.projectseele.sync_feedback",
    )) and "fieldCost - absorbed" in entity,
    "feedback derives from actual post-field hull loss rather than incoming attack amount",
)

gate(
    "sync.shared_readout_and_test_controls",
    "eva.getSynchronizationRatio(partialTick)" in hud
    and "unit.getSynchronizationRatio(0.0F)" in telemetry
    and all(token in commands for token in (
        'literal("pilot")', 'literal("sync")', 'literal("set")',
        "DoubleArgumentType.doubleArg(0.0D, 100.0D)",
    )) and all(token in doc for token in (
        "/seele pilot sync set 80", "17.5%", "Player Capability",
    )) and "validate_eva_sync_contract.py" in launcher,
    "HUD, Operations and operator tests consume the same authoritative value",
)

if ERRORS:
    print(f"EVA synchronization contract: FAIL ({len(ERRORS)} gate(s))")
    sys.exit(1)
print("EVA synchronization contract: PASS")