package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModItems;
import com.projectseele.world.S20MovingElevatorsAdapter;
import com.projectseele.world.S20PhysicalElevatorDirector;
import com.supermartijn642.movingelevators.MovingElevators;
import com.supermartijn642.movingelevators.blocks.ControllerBlockEntity;
import com.supermartijn642.movingelevators.elevator.ElevatorCage;
import com.supermartijn642.movingelevators.elevator.ElevatorGroup;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.HashMap;
import java.util.Map;

/** Opt-in actual Moving Elevators trips, exclusively in named disposable copies. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class CommandLiftReview
{
    private static final boolean ENABLED = Boolean.getBoolean("projectseele.commandLiftReview");
    private static final ResourceKey<Level> GEOFRONT = ResourceKey.create(
            Registries.DIMENSION, new ResourceLocation("projectseele", "geofront"));
    private static final int[] ROUTE = {-448, -423, -419, -409, -448, -566, -419};
    private static final S20PhysicalElevatorDirector.LiftSpec SPEC =
            S20PhysicalElevatorDirector.commandRearLift();
    private static int age, stage, timer, arrivalTicks, current = -419;
    private static boolean started, inTransit, sawMotion;
    private static volatile boolean finished;
    private static final Map<BlockPos, BlockState> cargo = new HashMap<>();

    private CommandLiftReview() {}

    @SubscribeEvent
    public static void clientTick(TickEvent.ClientTickEvent event)
    {
        if (!ENABLED || event.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        mc.options.pauseOnLostFocus = false;
        if (finished) mc.stop();
    }

    @SubscribeEvent
    public static void serverTick(TickEvent.ServerTickEvent event)
    {
        if (!ENABLED || finished || event.phase != TickEvent.Phase.END) return;
        var server = event.getServer();
        if (server.getPlayerList().getPlayers().isEmpty()) return;
        String world = server.getWorldPath(LevelResource.ROOT).normalize().getFileName().toString();
        if (!world.equals("SEELE_LIFT_REVIEW_R28_20260906")
                && !world.equals("SEELE_LIFT_REVIEW_PREVIEW_20260906"))
        {
            ProjectSeele.LOGGER.error("Command lift review REFUSED non-test world {}", world);
            finished = true;
            return;
        }
        try
        {
            ServerLevel level = server.getLevel(GEOFRONT);
            ServerPlayer player = server.getPlayerList().getPlayers().get(0);
            if (++age > 3600) throw new IllegalStateException("overall timeout");
            if (age == 1)
            {
                player.setGameMode(GameType.CREATIVE);
                player.setItemInHand(InteractionHand.MAIN_HAND, ItemStack.EMPTY);
                player.setItemInHand(InteractionHand.OFF_HAND, ItemStack.EMPTY);
                player.getAbilities().flying = false;
                player.onUpdateAbilities();
                player.teleportTo(level, 12.5, -419, 253.5, 180, 0);
            }
            if (age < 120) return;
            ControllerBlockEntity controller = (ControllerBlockEntity) level.getBlockEntity(new BlockPos(9, -566, 253));
            require(controller != null && controller.hasGroup(), "controller group ready");
            ElevatorGroup group = controller.getGroup();
            if (!started)
            {
                started = true;
                boolean nativeFalseCar = ElevatorCage.canCreateCage(level,
                        group.getCageAnchorBlockPos(-423), 5, 6, 5, null);
                require(nativeFalseCar, "reproduced native overlapping-source false positive");
                verifyOneSource(group, current);
                require(!S20MovingElevatorsAdapter.allowDisplayPress(group, -566, 0, player), "restricted floor stays locked");
                ProjectSeele.LOGGER.info("COMMAND LIFT REVIEW started {}: native bridge false-positive={}, guarded source={}", world, nativeFalseCar, current);
            }
            if (inTransit)
            {
                timer++;
                sawMotion |= group.isMoving();
                require(timer < 600, "trip timeout " + ROUTE[stage]);
                if (group.isMoving())
                {
                    arrivalTicks = 0;
                    return;
                }
                // Wait from arrival, not departure: a long trip may still
                // be decelerating at the old fixed 65-tick check point.
                if (++arrivalTicks < 50) return;
                require(sawMotion, "real smooth-cage movement occurred");
                int target = ROUTE[stage];
                verifyOneSource(group, target);
                verifyCargo(level, group, target);
                if (stage != 0)
                    require(Math.abs(player.getY() - target) < 0.55, "passenger arrived: " + player.getY() + " vs " + target);
                BlockPos panel = new BlockPos(10, target + 1, 253);
                require(level.getBlockState(panel).is(MovingElevators.button_block)
                        && level.getBlockState(panel.above()).is(MovingElevators.display_block), "selector travelled with cage");
                // At the short adjacent-floor trip the departure interlock
                // must have expired; test the complete authored door path.
                for (double z = 253.5; z <= 258.5; z += 0.25)
                    require(level.noCollision(player, new AABB(12.2, target + 0.01, z - 0.3,
                            12.8, target + 1.8, z + 0.3)), "arrival door clearance " + target + " z=" + z);
                ProjectSeele.LOGGER.info("COMMAND LIFT REVIEW PASS trip {}: {} -> {}, passengerY={}, whole cargo={}, doors clear",
                        stage + 1, current, target, player.getY(), cargo.size());
                current = target;
                inTransit = false;
                stage++;
                timer = 0;
                return;
            }
            if (++timer < 35) return;
            if (stage == ROUTE.length)
            {
                require(S20MovingElevatorsAdapter.handleExternalCall(player,
                        S20PhysicalElevatorDirector.exteriorCallPosition(SPEC.stops().get(3))), "same-floor call handled");
                require(!group.isMoving(), "same-floor call does not recapture cage");
                ProjectSeele.LOGGER.info("COMMAND LIFT REVIEW COMPLETE world={} trips={} source={} reload-ready", world, ROUTE.length, current);
                finished = true;
                return;
            }
            int target = ROUTE[stage];
            if (stage == 0)
                player.teleportTo(level, 12.5, target, 259.5, 180, 0);
            else
                player.teleportTo(level, 12.5, current, 253.5, 90, 0);
            if (target == -566)
                player.setItemInHand(InteractionHand.MAIN_HAND, ModItems.TERMINAL_DOGMA_ACCESS_CARD.get().getDefaultInstance());
            S20MovingElevatorsAdapter.prepareDoorsBeforeUse(player, new BlockPos(10, current + 1, 253));
            snapshotCargo(level, group, current);
            if (stage == 0)
                require(S20MovingElevatorsAdapter.handleExternalCall(player,
                        S20PhysicalElevatorDirector.exteriorCallPosition(SPEC.stops().get(1))), "external lower call handled");
            else
                group.onDisplayPress(current, group.getFloorNumber(target) - group.getFloorNumber(current), player);
            require(group.isMoving(), "trip started " + current + " -> " + target);
            inTransit = true;
            sawMotion = true;
            timer = 0;
            arrivalTicks = 0;
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("COMMAND LIFT REVIEW FAILED stage=" + stage + " age=" + age, exception);
            finished = true;
        }
    }

    private static void verifyOneSource(ElevatorGroup group, int y)
    {
        for (int i = 0; i < group.getFloorCount(); i++)
            require(group.isCageAvailableAt(i, true, null) == (group.getFloorYLevel(i) == y),
                    "unique complete cage at " + y + ", candidate=" + group.getFloorYLevel(i));
    }

    private static void snapshotCargo(ServerLevel level, ElevatorGroup group, int y)
    {
        cargo.clear();
        BlockPos anchor = group.getCageAnchorBlockPos(y);
        for (int x = 0; x < 5; x++)
            for (int dy = 0; dy < 6; dy++)
                for (int z = 0; z < 5; z++)
                {
                    if (z == 4 && x >= 1 && x <= 3 && dy >= 1 && dy <= 3) continue;
                    BlockPos offset = new BlockPos(x, dy, z);
                    cargo.put(offset, level.getBlockState(anchor.offset(offset)));
                }
    }

    private static void verifyCargo(ServerLevel level, ElevatorGroup group, int y)
    {
        BlockPos anchor = group.getCageAnchorBlockPos(y);
        cargo.forEach((offset, state) -> require(level.getBlockState(anchor.offset(offset)).equals(state),
                "whole cargo mismatch at " + anchor.offset(offset)));
    }

    private static void require(boolean condition, String message)
    {
        if (!condition) throw new IllegalStateException(message);
    }
}
