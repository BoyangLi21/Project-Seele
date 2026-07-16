package com.projectseele.visual;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.world.GeoFrontBuilder;
import com.projectseele.world.GeoFrontBuilder.GeoFrontAudit;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Builds, enters and audits the standalone GeoFront development dimension. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class GeoFrontCommands
{
    public static final ResourceKey<Level> GEOFRONT = ResourceKey.create(
            Registries.DIMENSION,
            new ResourceLocation(ProjectSeele.MODID, "geofront"));
    public static final BlockPos ORIGIN = new BlockPos(0, 32, 0);

    private static final String RETURN_DIMENSION = "SeeleGeoFrontReturnDimension";
    private static final String RETURN_X = "SeeleGeoFrontReturnX";
    private static final String RETURN_Y = "SeeleGeoFrontReturnY";
    private static final String RETURN_Z = "SeeleGeoFrontReturnZ";

    private GeoFrontCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("seele")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("geofront")
                        .then(Commands.literal("setup")
                                .executes(context -> setup(context.getSource())))
                        .then(Commands.literal("enter")
                                .executes(context -> enter(context.getSource())))
                        .then(Commands.literal("surface")
                                .executes(context -> surface(context.getSource())))
                        .then(Commands.literal("audit")
                                .executes(context -> audit(context.getSource())))
                        .then(Commands.literal("overview")
                                .executes(context -> overview(context.getSource())))));
    }

    private static int setup(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            source.sendFailure(Component.literal(
                    "GeoFront dimension is unavailable; verify the Project SEELE datapack."));
            return 0;
        }
        saveReturn(player);
        GeoFrontBuilder.build(level, ORIGIN);
        GeoFrontAudit result = GeoFrontBuilder.inspect(level, ORIGIN);
        logAudit("setup", result);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(
                    "GeoFront was built but failed audit: " + result.summary()));
            return 0;
        }
        teleportOverview(player, level);
        source.sendSuccess(() -> Component.literal(
                "GeoFront development sector ready. /seele geofront surface returns above."),
                false);
        return 1;
    }

    /** Fixed build used by the unattended GeoFront screenshot target. */
    static int setupVisualCapture(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            throw new IllegalStateException("GeoFront visual dimension is unavailable");
        }
        level.setDayTime(6000L);
        level.setWeatherParameters(12000, 0, false, false);
        GeoFrontBuilder.build(level, ORIGIN);
        GeoFrontAudit result = GeoFrontBuilder.inspect(level, ORIGIN);
        logAudit("visual-setup", result);
        if (!result.valid())
        {
            throw new IllegalStateException(
                    "GeoFront visual setup failed audit: " + result.summary());
        }
        BlockPos hiddenPlatform = ORIGIN.offset(0, -31, 0);
        level.setBlock(hiddenPlatform, net.minecraft.world.level.block.Blocks.BARRIER
                .defaultBlockState(), net.minecraft.world.level.block.Block.UPDATE_CLIENTS);
        player.stopRiding();
        player.teleportTo(level, hiddenPlatform.getX() + 0.5D,
                hiddenPlatform.getY() + 1.0D, hiddenPlatform.getZ() + 0.5D,
                180.0F, 0.0F);
        return 1;
    }

    private static int enter(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        GeoFrontAudit result = GeoFrontBuilder.inspect(level, ORIGIN);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(
                    "GeoFront has not passed setup. Run /seele geofront setup first."));
            return 0;
        }
        saveReturn(player);
        teleportOverview(player, level);
        return 1;
    }

    private static int surface(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        CompoundTag data = player.getPersistentData();
        ServerLevel destination = player.getServer().overworld();
        double x = destination.getSharedSpawnPos().getX() + 0.5D;
        double y = destination.getSharedSpawnPos().getY() + 1.0D;
        double z = destination.getSharedSpawnPos().getZ() + 0.5D;
        if (data.contains(RETURN_DIMENSION))
        {
            ResourceLocation location = ResourceLocation.tryParse(
                    data.getString(RETURN_DIMENSION));
            if (location != null)
            {
                ServerLevel stored = player.getServer().getLevel(ResourceKey.create(
                        Registries.DIMENSION, location));
                if (stored != null)
                {
                    destination = stored;
                    x = data.getDouble(RETURN_X);
                    y = data.getDouble(RETURN_Y);
                    z = data.getDouble(RETURN_Z);
                }
            }
        }
        player.stopRiding();
        player.teleportTo(destination, x, y, z, player.getYRot(), player.getXRot());
        source.sendSuccess(() -> Component.literal("Returned from GeoFront."), false);
        return 1;
    }

    private static int audit(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        GeoFrontAudit result = GeoFrontBuilder.inspect(level, ORIGIN);
        logAudit("command", result);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(result.summary()));
            return 0;
        }
        source.sendSuccess(() -> Component.literal(result.summary()), false);
        return 1;
    }

    private static int overview(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        teleportOverview(player, level);
        return 1;
    }

    public static ServerLevel geoFront(ServerPlayer player)
    {
        return player.getServer().getLevel(GEOFRONT);
    }

    private static void teleportOverview(ServerPlayer player, ServerLevel level)
    {
        player.stopRiding();
        player.teleportTo(level,
                ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + GeoFrontBuilder.OBSERVATION_Y + 1.0D,
                ORIGIN.getZ() + GeoFrontBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 16.0F);
    }

    private static void saveReturn(ServerPlayer player)
    {
        if (player.serverLevel().dimension().equals(GEOFRONT))
        {
            return;
        }
        CompoundTag data = player.getPersistentData();
        data.putString(RETURN_DIMENSION,
                player.serverLevel().dimension().location().toString());
        data.putDouble(RETURN_X, player.getX());
        data.putDouble(RETURN_Y, player.getY());
        data.putDouble(RETURN_Z, player.getZ());
    }

    private static void logAudit(String stage, GeoFrontAudit result)
    {
        if (result.valid())
        {
            ProjectSeele.LOGGER.info("GeoFront audit [{}]: {}", stage, result.summary());
        }
        else
        {
            ProjectSeele.LOGGER.error("GEOFRONT INVALID [{}]: {}", stage, result.summary());
        }
    }
}
