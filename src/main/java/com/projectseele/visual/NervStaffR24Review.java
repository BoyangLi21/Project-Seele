package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Real conversation packets and operator presses in the isolated R24 world. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID)
public final class NervStaffR24Review
{
    public static final boolean ENABLED = "r24-staff".equals(System.getProperty("projectseele.regionalBuild", ""));
    public static volatile boolean ready, finished;
    public static volatile String input = "", photo = "";
    public static final Set<String> inputs = java.util.concurrent.ConcurrentHashMap.newKeySet();
    public static final Set<String> photos = java.util.concurrent.ConcurrentHashMap.newKeySet();
    private static int state, timer, age, originalPresses, recoveryPresses;
    private static boolean preparePowered, launchPowered, recoveryPowered;
    private static Path world;
    private static ServerLevel level;
    private static ServerPlayer player;
    private static NervStaffEntity misato, ritsuko;
    private static UUID evaId, plugId;
    private static final JsonObject checks = new JsonObject();
    private static final JsonArray route = new JsonArray();

    private static void check(String name, boolean value)
    { checks.addProperty(name, value); if (!value) throw new IllegalStateException(name); }
    private static void next(int value)
    { state = value; timer = 0; input = ""; photo = ""; ProjectSeele.LOGGER.info("R24 STAFF REVIEW phase={}", value); }
    private static NervStaffEntity member(String key)
    { var id = NervStaffSavedData.get(level).identity(key); return id != null && level.getEntity(id) instanceof NervStaffEntity n ? n : null; }
    private static void load(BlockPos at)
    {
        for (int x = (at.getX() >> 4) - 1; x <= (at.getX() >> 4) + 1; x++)
            for (int z = (at.getZ() >> 4) - 1; z <= (at.getZ() >> 4) + 1; z++) level.getChunk(x, z);
    }
    private static boolean powered(String operation)
    {
        BlockPos at = NervOperationsConsole.staffControl(level, operation, 1);
        var block = level.getBlockState(at);
        return block.getBlock() instanceof ButtonBlock && block.getValue(ButtonBlock.POWERED);
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if (!ENABLED || !ready || finished || event.phase != TickEvent.Phase.END) return;
        try
        {
            var server = event.getServer(); if (server.getPlayerList().getPlayers().isEmpty()) return;
            if (world == null)
            {
                world = server.getWorldPath(LevelResource.ROOT).normalize();
                check("isolated_review_world", world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"));
                level = server.getLevel(FacilitySchemaV2.DIMENSION); player = server.getPlayerList().getPlayers().get(0);
                player.setGameMode(GameType.CREATIVE); player.stopRiding(); server.setFlightAllowed(true);
                player.getAbilities().flying = true; player.onUpdateAbilities();
                player.getInventory().add(new net.minecraft.world.item.ItemStack(com.projectseele.registry.ModItems.NERV_EMPLOYEE_CARD.get()));
                load(new BlockPos(29, -409, 284)); player.teleportTo(level, 27.5, -407, 282.5, 0, 0);
                for (int v = 0; v < 3; v++) EvaLogisticsDirector.loadControlTarget(level, v);
                TrainingPilotDirector.stop(level, 1);
            }
            level.resetEmptyTime(); age++; timer++;
            check("bounded_review", age < 14000);
            if (timer % 20 == 0 && misato != null)
            {
                JsonObject row = new JsonObject(); row.addProperty("age", age); row.addProperty("phase", state);
                row.addProperty("npc", misato.position().toString()); row.addProperty("pressed", misato.pressCount());
                row.addProperty("unit_phase", EvaLogisticsDirector.status(level, 1).phase()); route.add(row);
            }
            if (state == 0)
            {
                misato = member("misato"); ritsuko = member("ritsuko");
                if (misato == null || ritsuko == null || timer < 160) return;
                var eva = EvaLogisticsDirector.canonicalUnit(level, 1); var plug = EntryPlugDirector.canonical(level, 1);
                String coldPhase=EvaLogisticsDirector.status(level,1).phase();
                if(coldPhase.equals("DEPLOYED")||coldPhase.equals("PLUG_FAULT"))
                { var recovery=EvaLogisticsDirector.requestRecovery(level,1);check("fixture_recovery_from_prior_diagnostic",recovery.accepted());return; }
                if(Set.of("DESCENDING","TO_HANGAR","FILLING").contains(coldPhase))return;
                check("original_parked_fleet", eva != null && plug != null && EvaLogisticsDirector.status(level, 1).phase().equals("PARKED"));
                check("pilot_initially_absent", !NervStaffDialogue.boarded(level, 1)); evaId = eva.getUUID(); plugId = plug.getUUID();
                originalPresses = misato.pressCount(); recoveryPresses = ritsuko.pressCount();
                NervStaffDialogue.open(player, misato); next(1); photo = "dialogue_greeting"; return;
            }
            if (state == 1)
            {
                if (!photos.contains("dialogue_greeting")) return; input = "query";
                if (!inputs.contains("query") || timer < 80) return;
                check("question_did_not_press", misato.pressCount() == originalPresses && StaffCommandBookR24.order(misato) == null);
                check("question_did_not_prepare", EvaLogisticsDirector.status(level, 1).phase().equals("PARKED"));
                photo = "readiness_query"; if (photos.contains(photo)) next(2); return;
            }
            if (state == 2)
            {
                input = "deploy"; var job = StaffCommandBookR24.order(misato);
                if (!inputs.contains("deploy") || job == null || job.step != StaffCommandBookR24.Step.PILOT) return;
                check("awaits_real_boarding", misato.pressCount() == originalPresses && !misato.busy());
                check("second_operator_unit_lease", StaffCommandBookR24.request(player, ritsuko, "prepare", 1) == 0);
                var visitor = net.minecraftforge.common.util.FakePlayerFactory.get(level, new com.mojang.authlib.GameProfile(UUID.fromString("832bac57-1a61-4b43-a220-9dc905ef0024"), "R24_Visitor"));
                check("visitor_has_no_command_permission", !NervStaffDialogue.authorized(visitor));
                check("visitor_order_rejected", StaffCommandBookR24.request(visitor, ritsuko, "prepare", 0) == 0);
                check("other_requester_cannot_cancel", StaffCommandBookR24.cancel(visitor, misato, 1) == 0 && StaffCommandBookR24.order(misato) != null);
                next(3); photo = "waiting_for_pilot"; return;
            }
            if (state == 3)
            {
                if (!photos.contains("waiting_for_pilot")) return; input = "cancel";
                if (!inputs.contains("cancel") || StaffCommandBookR24.order(misato) != null) return;
                check("cancel_before_press", misato.pressCount() == originalPresses && !misato.busy()); next(4); return;
            }
            if (state == 4)
            {
                input = "redeploy"; var job = StaffCommandBookR24.order(misato);
                if (!inputs.contains("redeploy") || job == null || job.step != StaffCommandBookR24.Step.PILOT) return;
                next(5); input = "close"; return;
            }
            if (state == 5)
            {
                if (!inputs.contains("close") || timer < 30) return;
                check("closing_window_keeps_order", StaffCommandBookR24.order(misato) != null);
                var plug = EntryPlugDirector.canonical(level, 1);
                Vec3 hatch = plug.transformPlugMarker(EntryPlugKinematics.HATCH_PORTAL_CENTRE_P);
                Vec3 outward = plug.getCanonicalTransform().transformVector(EntryPlugKinematics.PILOT_VIEW_FORWARD_P).normalize();
                Vec3 eye = hatch.add(outward.scale(2.4)), look = hatch.subtract(eye);
                player.teleportTo(level, eye.x, eye.y - player.getEyeHeight(), eye.z,
                        (float) Math.toDegrees(Math.atan2(-look.x, look.z)), (float) -Math.toDegrees(Math.atan2(look.y, look.horizontalDistance())));
                plug.tryBoardFromHatch(player); check("real_original_hatch_boarding", plug.getFirstPassenger() == player);
                next(6); return;
            }
            if (state == 6)
            {
                preparePowered |= powered("prepare"); launchPowered |= powered("launch");
                var status = EvaLogisticsDirector.status(level, 1);
                check("no_plug_fault", !status.phase().equals("PLUG_FAULT"));
                if (timer % 100 == 0) ProjectSeele.LOGGER.info("R24 STAFF TRANSFER {} npc={} job={}", status.phase(), misato.position(), StaffCommandBookR24.order(misato) == null ? "done" : StaffCommandBookR24.order(misato).step);
                if (status.phase().equals("DEPLOYED") && StaffCommandBookR24.order(misato) == null)
                {
                    check("two_actual_operator_presses", misato.pressCount() == originalPresses + 2 && preparePowered && launchPowered);
                    check("remote_operator_order_completed", StaffCommandBookR24.order(misato) == null);
                    var eva = EvaLogisticsDirector.canonicalUnit(level, 1); check("surface_arrival", eva.getY() > 80.7);
                    next(7); return;
                }
                if (timer > 200 && StaffCommandBookR24.order(misato) == null && !status.phase().equals("DEPLOYED"))
                    throw new IllegalStateException("Order stopped before departure: " + status.phase());
                return;
            }
            if (state == 7)
            {
                if (timer < 180) return;
                check("pilot_radio_authorized", StaffConversationR24.radioAllowed(player));
                check("radio_contact_requested", StaffConversationR24.contact(player, "律子") == 1);
                next(8); photo = "pilot_radio"; return;
            }
            if (state == 8)
            {
                check("bounded_radio_connection",timer<400);
                if (!photos.contains("pilot_radio")) return; input = "recover";
                if (inputs.contains("recover")) { next(9); input = "close_radio"; } return;
            }
            if (state == 9)
            {
                // Radio contact may reload the same UUID into a new Java
                // entity instance after the pilot left the command room.
                var currentOperator=member("ritsuko");if(currentOperator!=null)ritsuko=currentOperator;
                recoveryPowered |= powered("recover");
                if (EvaLogisticsDirector.status(level, 1).phase().equals("PARKED"))
                {
                    checks.addProperty("recovery_press_count",ritsuko.pressCount()-recoveryPresses);
                    check("actual_recovery_press", ritsuko.pressCount() == recoveryPresses + 1);
                    check("actual_recovery_button_power", recoveryPowered);
                    check("same_original_eva", EvaLogisticsDirector.canonicalUnit(level, 1).getUUID().equals(evaId));
                    check("same_original_plug", EntryPlugDirector.canonical(level, 1).getUUID().equals(plugId));
                    player.stopRiding(); player.teleportTo(level, 27.5, -407, 282.5, 0, 0); next(10); return;
                }
                if (timer > 200 && StaffCommandBookR24.order(ritsuko) == null && EvaLogisticsDirector.status(level, 1).phase().equals("DEPLOYED"))
                    throw new IllegalStateException("Recovery order did not begin");
                return;
            }
            if (state == 10 && timer > 180)
            {
                var currentOperator=member("misato");if(currentOperator!=null)misato=currentOperator;
                check("operator_returned_to_post", misato.position().distanceTo(Vec3.atBottomCenterOf(misato.station())) < 1.2);
                finish("");
            }
        }
        catch (Exception failure) { ProjectSeele.LOGGER.error("R24 staff review failed", failure); finish(failure.toString()); }
    }
    private static void finish(String error)
    {
        if(player!=null&&level!=null){player.stopRiding();player.teleportTo(level,27.5,-407,282.5,0,0);}
        var report = new JsonObject(); report.addProperty("error", error); report.add("checks", checks); report.add("motion", route);
        report.addProperty("phase", state); report.addProperty("ticks", age);
        try { Files.writeString(world.resolve("r24_staff_review.json"), new GsonBuilder().setPrettyPrinting().create().toJson(report)); }
        catch (Exception failure) { ProjectSeele.LOGGER.error("R24 staff report failed", failure); }
        finished = true;
    }
    private NervStaffR24Review() {}
}
