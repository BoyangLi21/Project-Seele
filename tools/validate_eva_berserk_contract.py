#!/usr/bin/env python3
"""Fail-closed static contract for autonomous Unit-01 berserk."""

import json
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


entity = text("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
config = text("src/main/java/com/projectseele/config/SeeleConfig.java")
telemetry = text("src/main/java/com/projectseele/world/NervCommandTelemetry.java")
doc = text("docs/EVA_BERSERK_TEST.md")
launcher = text("tools/start_test.bat")
animation = json.loads(text(
    "src/main/resources/assets/projectseele/animations/eva_unit01.animation.json"))


gate(
    "berserk.configured_defaults",
    all(token in config for token in (
        'defineInRange("durationTicks", 900',
        'defineInRange("recoveryTicks", 6000',
        'defineInRange("healthThreshold", 0.15D',
        'defineInRange("syncThreshold", 60.0D',
        'defineInRange("damageMultiplier", 2.5D',
        'defineInRange("targetRange", 128',
    )),
    "15 percent hull, 60 percent sync, 45 seconds, five minutes and 2.5x damage are externalized",
)

gate(
    "berserk.strict_trigger",
    all(token in entity for token in (
        "private boolean canEnterBerserk()", "getUnitVariant() != UNIT_01",
        "this.getPowerTicks() > 0", "this.getHealth() <= this.getMaxHealth() * healthThreshold",
        "this.getPilotSynchronization() >= syncThreshold",
        "this.isCrucified()", "this.isLaunchSequenceActive()",
    )),
    "only occupied, depleted, critically damaged high-sync Unit-01 can trigger outside hard interlocks",
)

gate(
    "berserk.safe_ejection",
    all(token in entity for token in (
        "pilot.stopRiding()", "MobEffects.DAMAGE_RESISTANCE",
        "MobEffects.SLOW_FALLING", "msg.projectseele.berserk_triggered",
        "DATA_AT_ON, false", "DATA_WEAPON, WEAPON_FISTS",
    )),
    "control loss clears weapons/field and protects the ejected pilot from the giant dismount",
)

gate(
    "berserk.angel_only_ai",
    all(token in entity for token in (
        "findNearestBerserkTarget", "entity instanceof Angel && entity.isAlive()",
        "this.getNavigation().moveTo(target, 1.45D)",
        "this.getLookControl().setLookAt(target", "this.setTarget(",
    )),
    "the autonomous target selector cannot acquire players, passive mobs or other EVA units",
)

gate(
    "berserk.melee_semantics",
    all(token in entity for token in (
        "MELEE_FIST_DAMAGE * multiplier", "this.damageSources().mobAttack(this)",
        "this.berserkAttackCooldown = 10", '"melee_left" : "melee"',
    )) and "attacker.isMeleeWeapon()" in entity,
    "alternating claws retain EVA-melee A.T. Field interaction at the configured multiplier",
)

gate(
    "berserk.power_override_and_recovery",
    "if (this.isBerserk())" in entity
    and "this.entityData.set(DATA_POWER_TICKS, 0)" in entity
    and "(!this.isBerserk() && this.isPilotControlLocked())" in entity
    and all(token in entity for token in (
        "finishBerserk()", "EVA_BERSERK_RECOVERY_TICKS",
        "this.berserkRecoveryTicks > 0", "msg.projectseele.berserk_recovery",
    )),
    "biological override moves at zero battery, then a separate restart-safe lock rejects boarding",
)

gate(
    "berserk.persistent_command_state",
    all(token in entity for token in (
        "DATA_BERSERK", "DATA_BERSERK_TICKS",
        'tag.putBoolean("SeeleBerserk"', 'tag.putInt("SeeleBerserkTicks"',
        'tag.putInt("SeeleBerserkRecoveryTicks"',
        'tag.getBoolean("SeeleBerserk")', 'tag.getInt("SeeleBerserkRecoveryTicks")',
    )) and all(token in telemetry for token in (
        "BERSERK / AUTONOMOUS", "FORCED SHUTDOWN",
        "getBerserkTicks()", "getBerserkRecoveryTicks()",
    )),
    "active/recovery clocks survive reload and are visible in Operations",
)

roar = animation.get("animations", {}).get("animation.eva_unit01.berserk_roar", {})
gate(
    "berserk.visual_contract",
    roar.get("animation_length") == 1.6
    and all(name in roar.get("bones", {}) for name in (
        "head", "torso_upper", "arm_l", "arm_r", "forearm_l", "forearm_r"))
    and all(token in entity for token in (
        'triggerAnim("strike", "berserk_roar")',
        'triggerableAnim("berserk_roar", ANIM_BERSERK_ROAR)',
        "DustParticleOptions.REDSTONE", "SoundEvents.RAVAGER_ROAR",
    )),
    "a mirrored full-upper-body roar, red eye markers and a roar sound accompany control loss",
)

gate(
    "berserk.manual_and_launcher",
    all(token in doc for token in (
        "/seele pilot sync set 80", "SeelePowerTicks:0", "45 秒", "5 分钟",
    )) and "validate_eva_berserk_contract.py" in launcher,
    "accelerated manual trigger and startup regression gate are documented",
)

if ERRORS:
    print(f"EVA berserk contract: FAIL ({len(ERRORS)} gate(s))")
    sys.exit(1)
print("EVA berserk contract: PASS")