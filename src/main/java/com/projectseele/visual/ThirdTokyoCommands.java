package com.projectseele.visual;

import java.util.List;
import java.util.Locale;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.item.NervConstructionKitItem;
import com.projectseele.world.ThirdTokyoSurfaceBuilder;
import com.projectseele.world.ThirdTokyoSurfaceBuilder.DistrictAudit;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Builds and audits the connected NERV-to-Tokyo-3 sortie battlefield. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ThirdTokyoCommands
{
    private ThirdTokyoCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("seele")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("tokyo3")
                        .then(Commands.literal("setup")
                                .executes(context -> setup(context.getSource())))
                        .then(Commands.literal("audit")
                                .executes(context -> audit(context.getSource())))
                        .then(Commands.literal("overview")
                                .executes(context -> overview(context.getSource())))));
    }

    static int setup(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = player.serverLevel();
        if (player.isPassenger())
        {
            source.sendFailure(Component.literal(
                    "Dismount before constructing the Tokyo-3 sortie district."));
            return 0;
        }

        int minSurface = level.getMinBuildHeight() + 36;
        int maxSurface = level.getMaxBuildHeight() - 48;
        if (maxSurface < minSurface)
        {
            source.sendFailure(Component.literal(
                    "This dimension is too shallow for Tokyo-3 and its launch shafts."));
            return 0;
        }
        int surfaceY = Math.max(minSurface,
                Math.min(maxSurface, player.blockPosition().getY() - 1));
        BlockPos origin = new BlockPos(player.blockPosition().getX(), surfaceY,
                player.blockPosition().getZ());
        AABB area = new AABB(origin).inflate(150.0D, 72.0D, 150.0D);
        boolean existingComplex = !level.getEntitiesOfClass(EvaUnit01Entity.class, area,
                unit -> unit.isAlive() && unit.findLaunchBed() != null).isEmpty();
        if (existingComplex)
        {
            source.sendFailure(Component.literal(
                    "A NERV/Tokyo-3 complex already occupies this area. "
                            + "Use /seele tokyo3 audit or move at least 170 blocks."));
            return 0;
        }

        ThirdTokyoSurfaceBuilder.buildDistrict(level, origin);
        NervConstructionKitItem.buildComplex(level, origin);
        TokyoAudit result = inspect(level, origin);
        logAudit("setup", result);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(
                    "Tokyo-3 was built but failed structural audit: " + result.summary()));
            return 0;
        }
        teleportOverview(player, origin);
        source.sendSuccess(() -> Component.literal(
                "Tokyo-3 sortie district ready. /seele silo board enters Unit-01; "
                        + "/seele tokyo3 overview returns to the skyline deck."), false);
        return 1;
    }

    /** Fixed-world setup used by the unattended map screenshot target. */
    static int setupVisualCapture(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = player.serverLevel();
        player.stopRiding();
        BlockPos origin = fixedVisualOrigin(level);
        level.setDayTime(6000L);
        level.setWeatherParameters(12000, 0, false, false);
        AABB cleanup = new AABB(origin).inflate(160.0D, 96.0D, 160.0D);
        level.getEntitiesOfClass(EvaUnit01Entity.class, cleanup).forEach(Entity::discard);
        ThirdTokyoSurfaceBuilder.buildDistrict(level, origin);
        NervConstructionKitItem.buildComplex(level, origin);
        TokyoAudit result = inspect(level, origin);
        logAudit("visual-setup", result);
        if (!result.valid())
        {
            throw new IllegalStateException(
                    "Tokyo-3 visual setup failed structural audit: " + result.summary());
        }
        // Keep the real server player under the central apron so the complete
        // +/-104 district stays inside the chunk tracking square. The client
        // screenshot camera is independent and may still visit all four views.
        player.teleportTo(level, origin.getX() + 0.5D, origin.getY() - 20.0D,
                origin.getZ() + 13.5D, 180.0F, 0.0F);
        return 1;
    }

    static BlockPos fixedVisualOrigin(ServerLevel level)
    {
        return new BlockPos(0,
                Math.max(level.getMinBuildHeight() + 36,
                        Math.min(level.getMaxBuildHeight() - 48, 96)),
                0);
    }

    private static int audit(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        BlockPos origin = findOrigin(player);
        TokyoAudit result = inspect(player.serverLevel(), origin);
        logAudit("command", result);
        Component report = Component.literal(result.summary());
        if (result.valid())
        {
            source.sendSuccess(() -> report, false);
            return 1;
        }
        source.sendFailure(report);
        return 0;
    }

    private static int overview(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        BlockPos origin = findOrigin(player);
        player.stopRiding();
        teleportOverview(player, origin);
        source.sendSuccess(() -> Component.literal(
                "Tokyo-3 skyline observation deck."), false);
        return 1;
    }

    private static void teleportOverview(ServerPlayer player, BlockPos origin)
    {
        player.teleportTo(player.serverLevel(),
                origin.getX() + 0.5D,
                origin.getY() + ThirdTokyoSurfaceBuilder.OBSERVATION_Y + 1.0D,
                origin.getZ() + ThirdTokyoSurfaceBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 18.0F);
    }

    private static BlockPos findOrigin(ServerPlayer player)
    {
        AABB area = player.getBoundingBox().inflate(220.0D, 128.0D, 220.0D);
        EvaUnit01Entity centreUnit = player.serverLevel()
                .getEntitiesOfClass(EvaUnit01Entity.class, area,
                        unit -> unit.isAlive()
                                && unit.getUnitVariant() == EvaUnit01Entity.UNIT_01
                                && unit.findLaunchBed() != null).stream()
                .min((left, right) -> Double.compare(
                        left.distanceToSqr(player), right.distanceToSqr(player)))
                .orElseThrow(() -> new IllegalStateException(
                        "No central Unit-01 launch bay within 220 blocks."));
        return centreUnit.findLaunchBed().above(30);
    }

    private static TokyoAudit inspect(ServerLevel level, BlockPos origin)
    {
        DistrictAudit district = ThirdTokyoSurfaceBuilder.inspect(level, origin);
        List<EvaUnit01Entity> units = level.getEntitiesOfClass(EvaUnit01Entity.class,
                new AABB(origin).inflate(80.0D, 64.0D, 80.0D),
                unit -> unit.isAlive() && unit.findLaunchBed() != null);
        boolean has00 = units.stream().anyMatch(
                unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_00);
        boolean has01 = units.stream().anyMatch(
                unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_01);
        boolean has02 = units.stream().anyMatch(
                unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_02);
        boolean variants = has00 && has01 && has02;
        return new TokyoAudit(district.valid() && units.size() == 3 && variants,
                district, units.size(), variants);
    }

    private static void logAudit(String stage, TokyoAudit result)
    {
        if (result.valid())
        {
            ProjectSeele.LOGGER.info("Tokyo-3 district audit [{}]: {}",
                    stage, result.summary());
        }
        else
        {
            ProjectSeele.LOGGER.error("TOKYO-3 DISTRICT INVALID [{}]: {}",
                    stage, result.summary());
        }
    }

    private record TokyoAudit(boolean valid, DistrictAudit district,
                              int units, boolean variants)
    {
        String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s units=%d variants00/01/02=%s | %s",
                    this.valid, this.units, this.variants, this.district.summary());
        }
    }
}
