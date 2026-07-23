#!/usr/bin/env python3
"""Fail-closed static contract for the single-player NERV pilot rehearsal."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    target = ROOT / path
    if not target.is_file():
        raise AssertionError(f"missing {path}")
    return target.read_text(encoding="utf-8")


def require(label: str, value: bool, detail: str) -> None:
    print(f"[{'PASS' if value else 'FAIL'}] {label}: {detail}")
    if not value:
        raise AssertionError(label)


def main() -> int:
    entities = read("src/main/java/com/projectseele/registry/ModEntities.java")
    common = read("src/main/java/com/projectseele/CommonEvents.java")
    client = read("src/main/java/com/projectseele/client/ClientEvents.java")
    plug = read("src/main/java/com/projectseele/entity/EntryPlugCarrierEntity.java")
    director = read("src/main/java/com/projectseele/world/EntryPlugDirector.java")
    training = read("src/main/java/com/projectseele/world/TrainingPilotDirector.java")
    eva = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
    phases = read("src/main/java/com/projectseele/world/EvaFleetSavedData.java")
    logistics = read("src/main/java/com/projectseele/world/EvaLogisticsDirector.java")
    hangar = read("src/main/java/com/projectseele/world/EvaHangarBuilder.java")
    operations = read(
        "src/main/java/com/projectseele/world/NervOperationsCentreBuilder.java"
    )
    video = read(
        "src/main/java/com/projectseele/network/ServerboundEvaVideoFramePacket.java"
    )
    game_events = read("src/main/java/com/projectseele/GameEvents.java")

    require(
        "dummy.entity",
        all(token in entities for token in (
            "TRAINING_PILOT", "ENTRY_PLUG_CARRIER"
        )) and "TRAINING_PILOT" in common and "ENTRY_PLUG_CARRIER" in common
        and "TrainingPilotRenderer" in client
        and "EntryPlugCarrierRenderer" in client,
        "pilot and physical entry plug are registered server/client side",
    )
    require(
        "dummy.external_boarding",
        all(token in plug for token in (
            "boardPassenger", "STAGE_SUSPENDED", "STAGE_INSERTING",
            "canAddPassenger"
        )) and all(token in training for token in (
            "EntryPlugDirector.ensureSuspended", "plug.boardPassenger(pilot)",
            "STAGE_IN_PLUG"
        )),
        "visible dummy walks to and occupies the same plug as a human",
    )
    require(
        "dummy.physical_insertion",
        all(token in director for token in (
            "suspendedPosition", "tickInsertion", "START_REAR_OFFSET",
            "SEATED_TILT", "boardFromExternalPlug"
        )) and "boardFromExternalPlug(Entity passenger)" in eva,
        "passenger-carrying plug follows a diagonal world-space path",
    )
    require(
        "dummy.bounded_plug_lookup",
        all(token in director for token in (
            "CACHED_PLUGS", "getEntitiesOfClass(EntryPlugCarrierEntity.class",
            "AABB search", "resetRuntime"
        )) and "level.getAllEntities()" not in director
        and "EntryPlugDirector.resetRuntime()" in game_events,
        "parked plug lookup is cached/local and is cleared with server runtime state",
    )
    require(
        "dummy.phase_order",
        all(token in phases for token in (
            "BRIDGE_RETRACTING", "PLUG_INSERTING", "PLUG_LOCKING",
            "DRAINING", "TO_SILO"
        )) and all(token in logistics for token in (
            "Phase.BRIDGE_RETRACTING", "Phase.PLUG_INSERTING",
            "Phase.PLUG_LOCKING", "EntryPlugDirector.hasBoardedPilot"
        )),
        "bridge, plug, lock and drain are explicit persistent phases",
    )
    require(
        "dummy.hangar_stage",
        all(token in hangar for token in (
            "OBSERVATION_FLOOR_Y", "setBoardingBridgeExtension",
            "buildObservationControlRoom", "buildPlugCraneRig"
        )) and all(token in operations for token in (
            "linkHangars", "hasConnectedHangarRoutes", "hangarRoutes"
        )),
        "three overhead booths, split bridges, crane rigs and sealed routes exist",
    )
    require(
        "dummy.command_feed",
        all(token in training for token in (
            "tickFeeds", "trainingFrame", "relayTrainingFrame"
        )) and all(token in video for token in (
            "hasCommandViewers", "relayTrainingFrame", "isHumanFeedActive"
        )),
        "server-rendered training optical feed yields to a real human feed",
    )
    print("Dummy pilot / external entry-plug contract is complete.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"Dummy pilot contract failed: {error}", file=sys.stderr)
        raise SystemExit(1)

