#!/usr/bin/env python3
"""Structural regression gate for EVA firearm, scope and strategic blasts."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
failures: list[str] = []


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def require(name: str, condition: bool, detail: str) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {detail}")
    if not condition:
        failures.append(name)


entity = read("src/main/java/com/projectseele/entity/EvaUnit01Entity.java")
renderer = read("src/main/java/com/projectseele/client/render/EvaUnit01Renderer.java")
client = read("src/main/java/com/projectseele/client/ClientForgeEvents.java")
hud = read("src/main/java/com/projectseele/client/EvaHud.java")
director = read("src/main/java/com/projectseele/fx/StrategicExplosionDirector.java")
network = read("src/main/java/com/projectseele/network/SeeleNetwork.java")
control_packet = read("src/main/java/com/projectseele/network/ServerboundEvaControlPacket.java")
config = read("src/main/java/com/projectseele/config/SeeleConfig.java")
visual_capture = read(
    "src/main/java/com/projectseele/client/visual/VisualCaptureManager.java")
visual_automation = read(
    "src/main/java/com/projectseele/visual/VisualLabAutomation.java")

require("aim.bedrock_sign",
        'setRotX(-pitch)' in renderer and 'setRotX(pitch)' not in renderer,
        "visible Bedrock pitch negates Minecraft XRot")
require("aim.shared_envelope",
        "player.setXRot(pitch)" in client
        and "MIN_CANNON_AIM_PITCH" in client
        and "MAX_CANNON_AIM_PITCH" in client
        and "MIN_CANNON_AIM_PITCH = -55.0F" in entity
        and "MAX_CANNON_AIM_PITCH = 55.0F" in entity
        and entity.count("this.pilotAimDirection(pilot)") >= 2
        and "Vec3.directionFromRotation(pitch, pilot.getYRot())" in entity,
        "camera, optical reticle and release-frame server ray share one -55..+55 envelope")
require("scope.optical_feed",
        'hideSubtree' in renderer and 'WEAPON_CANNON' in renderer
        and 'yashima_fire_control' in hud and hud.count("drawDiamond") >= 5,
        "first person stows the giant cannon and renders converging acquisition symbols")

rifle_start = entity.index("public void fireRifle")
rifle_end = entity.index("private void detonateN2", rifle_start)
rifle_body = entity[rifle_start:rifle_end]
require("rifle.non_explosive",
        "ClientboundRifleTracerPacket" in rifle_body and ".explode(" not in rifle_body
        and "EVA_RIFLE_DAMAGE" in rifle_body,
        "automatic rifle uses damage + tracer with no explosion call")
require("rifle.networked_automatic",
        "ACTION_RIFLE_FIRE" in client and "ACTION_RIFLE_FIRE" in control_packet
        and "ClientboundRifleTracerPacket" in network,
        "held attack requests a server-authoritative automatic shot")
require("rifle.triggered_recoil",
        'this.triggerAnim("strike", this.isPilotProne()' in rifle_body
        and '"prone_rifle_fire" : "rifle_fire"' in rifle_body
        and '.triggerableAnim("rifle_fire", ANIM_RIFLE_FIRE)' in entity
        and '.triggerableAnim("prone_rifle_fire", ANIM_PRONE_RIFLE_FIRE)' in entity,
        "every accepted automatic shot triggers a stance-preserving recoil clip")
require("attacks.trigger_controller",
        "isPlayingTriggeredAnimation()" in entity
        and "? PlayState.CONTINUE : PlayState.STOP" in entity
        and ".receiveTriggeredAnimations()" in entity,
        "triggered melee/knife/lance/fire clips survive the controller predicate")
live_names = ("live_melee", "live_knife", "live_knife_heavy",
              "live_lance", "live_rifle", "live_jump")
require("attacks.live_visual_matrix",
        all(name in visual_automation and name in visual_capture
            for name in live_names)
        and "ServerboundEvaControlPacket(action)" in visual_capture
        and "LIVE_ATTACK_VIEWS" in visual_capture,
        "full Visual Lab runs real player input in external and first-person views")
require("rifle.visual_muzzle_socket",
        "rifleMuzzlePosition(dir)" in rifle_body
        and "RIFLE_STANDING_MUZZLE_FORWARD = 18.3308D" in entity
        and "RIFLE_PRONE_MUZZLE_FORWARD = 19.9715D" in entity
        and "pitchedUp.scale(muzzleUp)" in entity,
        "tracer and sound originate at the measured standing/prone visible muzzle")
require("cannon.visual_muzzle_socket",
        "cannonMuzzlePosition(dir)" in entity
        and "CANNON_STANDING_MUZZLE_FORWARD = 22.4417D" in entity
        and "CANNON_PRONE_MUZZLE_FORWARD = 23.9289D" in entity
        and "new ClientboundCannonBeamPacket(muzzle.x, muzzle.y, muzzle.z" in entity,
        "positron beam originates at the measured standing/prone barrel cap")
require("melee.humanoid_claw",
        'claw_strike("r")' in read("tools/make_tiger_unit01_pack.py")
        and 'claw_strike("l")' in read("tools/make_tiger_unit01_pack.py")
        and 'for attack_name in ("smash", "stomp")' in read(
            "tools/make_tiger_unit01_pack.py"),
        "bare attacks retain animated claw fingers instead of a static golem fist")
require("knife.single_hand_heavy",
        '"knife_heavy"' in entity
        and '"prone_knife_heavy"' in entity
        and '"crouch_knife_heavy"' in entity
        and "knife ?" in entity,
        "knife RMB selects a longer stance-safe one-handed reverse-grip slash")
require("jump.takeoff",
        "JUMP_VELOCITY = 5.40D" in entity
        and 'this.triggerAnim("strike", "takeoff")' in entity
        and '.triggerableAnim("takeoff", ANIM_TAKEOFF)' in entity,
        "jump has a dedicated takeoff clip and the reviewed giant-scale impulse")
require("jump.request_deduplication",
        "public final int requestId" in control_packet
        and "buf.writeVarInt(this.requestId)" in control_packet
        and "eva.pilotJump(sender, this.requestId)" in control_packet
        and "jumpRequestId = ++jumpRequestIdCounter" in client
        and "requestId == this.lastJumpRequestId" in entity
        and "this.clientJumpImpulsePending = this.isControlledByLocalInstance()" in entity,
        "each physical key press has one server request ID and only the local pilot applies its impulse")
require("unit02.longinus",
        "return LONGINUS_MESH;" in renderer
        and "return LONGINUS_TEXTURE;" in renderer,
        "Unit-02 temporarily uses the common reviewed Longinus polearm")

angel_files = [
    "RamielEntity.java", "SachielEntity.java", "ShamshelEntity.java",
    "ZeruelEntity.java", "IsrafelEntity.java",
]
angel_contract = all("isMeleeWeapon()" in read(f"src/main/java/com/projectseele/entity/{name}")
                     for name in angel_files)
require("at_field.melee_only", angel_contract,
        "all five Angel implementations distinguish EVA contact from rifle/cannon fire")

require("n2.threefold",
        "CANNON_EXPLOSION_RADIUS.get() * 3.0D" in director
        and "CANNON_TERRAIN_RADIUS.get() * 3" in director
        and "CANNON_CRATER_DEPTH.get() * 3" in director
        and "CANNON_BLAST_DAMAGE.get().floatValue() * 3.0F" in director
        and "10.8F, false" in entity
        and "3.6F, false" in entity,
        "N2 radius, depth, damage and non-cross visual are exactly 3x cannon")
require("blast.staged_server_thread",
        "ServerTickEvent" in director and "STRATEGIC_BLOCKS_PER_TICK" in director
        and "Thread" not in director and "CompletableFuture" not in director,
        "terrain writes are budgeted on the main server tick")
require("blast.mountain_defaults",
        'defineInRange("terrainRadius", 64' in config
        and 'defineInRange("craterDepth", 32' in config
        and 'defineInRange("blocksPerTick", 2048' in config,
        "defaults carve a 64x32 cannon crater under a 2048-block/tick budget")
require("blast.optical_overexposure",
        "nuclearFlashOpacity" in read(
            "src/main/java/com/projectseele/client/fx/ClientFxManager.java")
        and "NUCLEAR_FLASH" in hud,
        "strategic detonations drive a distance-scaled, FX-configurable screen flash")

mesh_path = ROOT / "run/resourcepacks/eva_real_model/assets/projectseele/mesh/eva_pallet_smg.mesh.json"
mesh_ok = False
if mesh_path.exists():
    mesh = json.loads(mesh_path.read_text(encoding="utf-8"))
    source_root = ROOT / "external-assets/work/pallet-rifle-oni/palett"
    source_installed = ((source_root / "palett.obj").is_file()
                        and (source_root / "palett.bmp").is_file())
    if source_installed:
        mesh_ok = (
            mesh.get("triangle_count") == 292
            and set(mesh.get("parts", {})) == {"cannon"}
            and mesh.get("local_only") is True
            and mesh.get("release_approved") is False
            and mesh.get("source_sha256", {}).get("obj")
            == "e82f47eaaa1528208b165b50a1979b153b01cb8c8b92114abd9f371cc2d4dd6f"
        )
    else:
        mesh_ok = (
            mesh.get("triangle_count") == 240
            and set(mesh.get("parts", {})) == {"cannon"}
        )
require("rifle.mesh", mesh_ok,
        "TV Pallet Rifle is 292 triangles when locally installed; otherwise the "
        "240-triangle original fallback occupies the semantic cannon socket")

for locale in ("en_us", "zh_cn"):
    language = json.loads(read(f"src/main/resources/assets/projectseele/lang/{locale}.json"))
    require(f"lang.{locale}", all(key in language for key in (
        "msg.projectseele.weapon_rifle", "msg.projectseele.weapon_n2",
        "hud.projectseele.yashima_fire_control", "hud.projectseele.n2_arming")),
        "rifle, N2 and optical-fire-control strings are present")

if failures:
    print("Weapon systems contract: FAIL (" + ", ".join(failures) + ")")
    sys.exit(1)
print("Weapon systems contract: PASS")
