package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModItems;
import com.projectseele.world.*;
import com.supermartijn642.movingelevators.blocks.ControllerBlockEntity;
import com.supermartijn642.movingelevators.elevator.ElevatorGroup;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Native passenger trips through every retained personnel lift, in the preview only. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class TvPersonnelLiftChecks
{
    private static final String MODE=System.getProperty("projectseele.tvWorldPreviewReview", "");
    private static final boolean ENABLED = MODE.equals("lifts")||MODE.equals("lifts-surface")||MODE.equals("lifts-cages")||MODE.equals("lifts-commander")||MODE.equals("lifts-command");
    private static final int FIRST_LIFT=MODE.equals("lifts-cages")?1:MODE.equals("lifts-surface")?3:0;
    private static final int LAST_LIFT=MODE.equals("lifts-cages")?3:Integer.MAX_VALUE;
    private static final List<String> TRACE = new ArrayList<>();
    private static final Map<BlockPos, BlockState> SHELL = new HashMap<>();
    private static final List<Integer> ROUTE = new ArrayList<>();
    private static int lift=FIRST_LIFT;
    private static int age, timer, trip, source, initial, arrival, totalTrips;
    private static boolean entered, ready, moving;
    private static volatile boolean done;
    private static double previousY, maxStep;
    private static ItemStack savedMainHand;
    private static net.minecraft.world.phys.Vec3 savedPosition;
    private static net.minecraft.resources.ResourceKey<net.minecraft.world.level.Level> savedDimension;
    private static GameType savedMode;
    private static float savedYaw,savedPitch;
    private static boolean savedFlying;
    private static boolean optionsSaved, savedPause;
    private static int savedDistance;

    private TvPersonnelLiftChecks() {}

    @SubscribeEvent
    public static void client(TickEvent.ClientTickEvent event)
    {
        if (!ENABLED || event.phase != TickEvent.Phase.END) return;
        var mc = Minecraft.getInstance();
        if (!optionsSaved)
        {
            optionsSaved=true;savedPause=mc.options.pauseOnLostFocus;savedDistance=mc.options.renderDistance().get();
            mc.options.pauseOnLostFocus=false;mc.options.renderDistance().set(6);
        }
        if(done)
        {
            mc.options.pauseOnLostFocus=savedPause;mc.options.renderDistance().set(savedDistance);
            mc.stop();
        }
    }

    @SubscribeEvent
    public static void server(TickEvent.ServerTickEvent event)
    {
        if (!ENABLED || done || event.phase != TickEvent.Phase.END) return;
        var server = event.getServer();
        if (server.getPlayerList().getPlayers().isEmpty()) return;
        var world = server.getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))
            throw new IllegalStateException("TV lift review refused another save");
        try
        {
            require(++age < 18000, "overall timeout");
            ServerLevel level = server.getLevel(FacilitySchemaV2.DIMENSION);
            ServerPlayer player = server.getPlayerList().getPlayers().get(0);
            var specs = S20PhysicalElevatorDirector.s20Lifts(level);
            if(MODE.equals("lifts-commander"))specs=specs.stream().filter(spec->spec.id().equals(S20PhysicalElevatorDirector.COMMANDER_OFFICE_LIFT_ID)).toList();
            if(MODE.equals("lifts-command"))specs=specs.stream().filter(spec->spec.id().equals(S20PhysicalElevatorDirector.commandRearLift().id())).toList();
            if (lift == Math.min(specs.size(),LAST_LIFT))
            {
                log("COMPLETE lifts=" + (lift-FIRST_LIFT) + " firstLift="+FIRST_LIFT+" passengerTrips=" + totalTrips + " maxStep=" + maxStep);
                Files.writeString(world.resolve("tv_preview_lift_checks.txt"), String.join("\n", TRACE));
                Files.deleteIfExists(world.resolve("tv_preview_lift_failure.txt"));
                restore(player);
                done = true;
                return;
            }
            var spec = specs.get(lift);
            BlockPos centre = spec.lower().cabinCentre();
            if (!entered)
            {
                entered = true;
                if(savedPosition==null){savedPosition=player.position();savedDimension=player.level().dimension();savedMode=player.gameMode.getGameModeForPlayer();savedYaw=player.getYRot();savedPitch=player.getXRot();savedFlying=player.getAbilities().flying;}
                player.setGameMode(GameType.CREATIVE);
                player.getAbilities().flying = false;
                player.onUpdateAbilities();
                if (savedMainHand == null) savedMainHand = player.getMainHandItem().copy();
                player.setItemInHand(InteractionHand.MAIN_HAND, ModItems.TERMINAL_DOGMA_ACCESS_CARD.get().getDefaultInstance());
                player.teleportTo(level, centre.getX() + .5, centre.getY(), centre.getZ() + .5, 0, 0);
                timer = 0;
            }
            Direction wall = spec.id().equals(S20PhysicalElevatorDirector.OBSERVATION_HANGAR_LIFT_ID)
                    || spec.id().equals(S20PhysicalElevatorDirector.COMPACT_CAGE_LIFT_ID)
                    ? Direction.EAST : spec.lower().exit().getClockWise();
            int distance = spec.id().equals(S20PhysicalElevatorDirector.SURFACE_TRANSIT_LIFT_ID) ? 4 : 3;
            var blockEntity = level.getBlockEntity(centre.relative(wall, distance));
            if (++timer < 120 && !ready) return;
            require(blockEntity instanceof ControllerBlockEntity, "retained controller " + spec.id());
            var controller = (ControllerBlockEntity) blockEntity;
            require(controller.hasGroup(), "retained group " + spec.id());
            ElevatorGroup group = controller.getGroup();
            if (!ready)
            {
                if(group.isMoving()){player.getAbilities().flying=true;player.onUpdateAbilities();return;}
                player.getAbilities().flying=false;player.onUpdateAbilities();
                int found = 0;
                for (int floor = 0; floor < group.getFloorCount(); floor++)
                    if (group.isCageAvailableAt(floor, true, null))
                    {
                        source = group.getFloorYLevel(floor);
                        found++;
                    }
                require(found == 1, "one complete cabin " + spec.id() + " found=" + found);
                initial = source;
                ROUTE.clear();
                for (var stop : spec.stops()) if (stop.walkY() != source) ROUTE.add(stop.walkY());
                int finalFloor=Integer.getInteger("projectseele.liftReturnY",initial);
                require(spec.stops().stream().anyMatch(stop->stop.walkY()==finalFloor),"valid return floor");
                if(ROUTE.isEmpty()||ROUTE.get(ROUTE.size()-1)!=finalFloor)ROUTE.add(finalFloor);
                // Let the client acknowledge the setup teleport before the native
                // car moves, especially on the long surface lift.
                player.teleportTo(level,centre.getX()+.5,source,centre.getZ()+.5,0,0);
                player.fallDistance=0;player.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);player.setOnGround(true);
                ready = true;
                timer = 0;
                log("START " + spec.id() + " source=" + source + " route=" + ROUTE);
                return;
            }
            if (moving)
            {
                double step = Math.abs(player.getY() - previousY);
                if(spec.id().equals(S20PhysicalElevatorDirector.SURFACE_TRANSIT_LIFT_ID)&&(timer%10==0||step>=8))
                    log("SAMPLE surface player="+player.getY()+" previous="+previousY+" cage="+group.getCurrentY()+" lastCage="+group.getLastY()+" targetSpeed="+group.getTargetSpeed());
                previousY = player.getY();
                maxStep = Math.max(step, maxStep);
                require(step < 10, "passenger movement continuity " + step+" player="+player.getY()+" cage="+group.getCurrentY()+" lastCage="+group.getLastY());
                require(timer < 2400, "native trip timeout " + spec.id());
                if (group.isMoving()) { arrival = 0; return; }
                if (++arrival < 60) return;
                int target = ROUTE.get(trip);
                require(Math.abs(player.getY() - target) < .6, "passenger arrival " + player.getY() + " target=" + target);
                BlockPos anchor = group.getCageAnchorBlockPos(target);
                SHELL.forEach((offset, state) -> require(level.getBlockState(anchor.offset(offset)).equals(state),
                        "whole cabin floor/roof " + anchor.offset(offset)));
                var landing = spec.stops().stream().filter(stop -> stop.walkY() == target).findFirst().orElseThrow();
                for (double d = 0; d <= 6; d += .25)
                {
                    double x = centre.getX() + .5 + landing.exit().getStepX() * d;
                    double z = centre.getZ() + .5 + landing.exit().getStepZ() * d;
                    require(level.noCollision(player, new AABB(x - .3, target + .01, z - .3,
                            x + .3, target + 1.8, z + .3)), "arrival door " + spec.id() + " d=" + d);
                }
                log("PASS " + spec.id() + " " + source + " -> " + target + " passenger=" + player.getY());
                source = target;
                trip++; totalTrips++; timer = 0; moving = false;
                return;
            }
            if (timer < 35) return;
            if (trip == ROUTE.size())
            {
                lift++; trip = 0; timer = 0; entered = false; ready = false;
                return;
            }
            require(Math.abs(player.getY()-source)<.6,"passenger settled on source car before departure");
            S20MovingElevatorsAdapter.prepareDoorsBeforeUse(player, centre.atY(source).relative(wall, distance - 1).above());
            BlockPos anchor = group.getCageAnchorBlockPos(source);
            SHELL.clear();
            for (int x = 0; x < group.getCageSizeX(); x++)
                for (int z = 0; z < group.getCageSizeZ(); z++)
                    for (int y : new int[]{0, group.getCageSizeY() - 1})
                    {
                        BlockPos offset = new BlockPos(x, y, z);
                        SHELL.put(offset, level.getBlockState(anchor.offset(offset)));
                    }
            int target = ROUTE.get(trip);
            group.onDisplayPress(source, group.getFloorNumber(target) - group.getFloorNumber(source), player);
            require(group.isMoving(), "native departure accepted " + spec.id() + " target=" + target);
            previousY = player.getY(); timer = 0; arrival = 0; moving = true;
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("TV LIFT CHECKS FAILED lift=" + lift + " trip=" + trip, exception);
            restore(server.getPlayerList().getPlayers().get(0));
            try { Files.writeString(world.resolve("tv_preview_lift_failure.txt"), String.join("\n", TRACE) + "\n" + exception); }
            catch (Exception ignored) { }
            done = true;
        }
    }

    private static void require(boolean condition, String reason)
    {
        if (!condition) throw new IllegalStateException(reason);
    }
    private static void restore(ServerPlayer player)
    {
        if(savedMainHand!=null)player.setItemInHand(InteractionHand.MAIN_HAND,savedMainHand);
        if(savedMode!=null)player.setGameMode(savedMode);
        if(savedPosition!=null)player.teleportTo(player.server.getLevel(savedDimension),savedPosition.x,savedPosition.y,savedPosition.z,savedYaw,savedPitch);
        player.fallDistance=0;player.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
        player.getAbilities().flying=savedFlying;player.onUpdateAbilities();
    }
    private static void log(String line)
    {
        TRACE.add(line);
        ProjectSeele.LOGGER.info("TV LIFT CHECKS {}", line);
    }
}
