#!/usr/bin/env python3
"""Fail-closed static contract for Project SEELE LCL gameplay."""

from pathlib import Path
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


fluid = text("src/main/java/com/projectseele/fluid/LclFluidType.java")
events = text("src/main/java/com/projectseele/event/LclEvents.java")
config = text("src/main/java/com/projectseele/config/SeeleConfig.java")
registry = text("src/main/java/com/projectseele/registry/ModFluids.java")
landscape = text("src/main/java/com/projectseele/world/GeoFrontLandscapeBuilder.java")
dogma = text("src/main/java/com/projectseele/world/TerminalDogmaBuilder.java")
doc = text("docs/LCL_TEST.md")


gate(
    "lcl.independent_fluid",
    all(token in registry for token in (
        "DeferredRegister<FluidType>", "LCL_TYPE", "LCL_SOURCE", "FLOWING_LCL"
    )) and ".block(ModBlocks.LCL_BLOCK)" in registry,
    "dedicated source/flowing fluid never replaces vanilla water",
)

gate(
    "lcl.breathable_swimmable",
    all(token in fluid for token in (
        ".canSwim(true)", ".canDrown(false)", ".canPushEntity(true)"
    )) and "setAirSupply(living.getMaxAirSupply())" in events,
    "submerged entities can swim and receive server-authoritative oxygen",
)

gate(
    "lcl.player_recovery",
    "living instanceof ServerPlayer" in events
    and "living.heal((float) amount)" in events
    and "living.tickCount % interval == 0" in events
    and "LCL_HEAL_AMOUNT" in config
    and 'defineInRange("healAmount", 1.0D' in config
    and "LCL_HEAL_INTERVAL_TICKS" in config
    and 'defineInRange("healIntervalTicks", 40' in config,
    "players recover one health point every forty ticks by default",
)

gate(
    "lcl.item_persistence",
    "ItemExpireEvent" in events
    and "touchesLcl(item)" in events
    and "event.setExtraLife(ITEM_LIFETIME_EXTENSION_TICKS)" in events
    and "event.setCanceled(true)" in events
    and "LCL_ITEMS_PERSIST" in config
    and 'define("itemsPersist", true)' in config,
    "expired drops are renewed only while touching LCL and remain configurable",
)

gate(
    "lcl.facility_usage",
    "ModFluids.LCL_SOURCE.get().defaultFluidState()" in landscape
    and "ModFluids.LCL_SOURCE.get().defaultFluidState()" in dogma,
    "GeoFront lake and Terminal Dogma pool use the same gameplay fluid",
)

gate(
    "lcl.manual_test_contract",
    all(token in doc for token in (
        "projectseele:lcl", "/damage @s 6", "Age:5990s",
        "healAmount", "healIntervalTicks", "itemsPersist"
    )),
    "manual oxygen, healing, expiry and config checks are documented",
)

if ERRORS:
    print(f"LCL contract: FAIL ({len(ERRORS)} gate(s))")
    sys.exit(1)
print("LCL contract: PASS")