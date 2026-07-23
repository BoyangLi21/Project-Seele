package com.projectseele.visual;

import java.util.Locale;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.world.EvaHangarBuilder;
import com.projectseele.world.EvaLogisticsDirector;
import com.projectseele.world.EvaLogisticsDirector.ActionResult;
import com.projectseele.world.EvaLogisticsDirector.Status;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.Tokyo3RecoveryConsole;
import com.projectseele.world.TrainingPilotDirector;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Operator commands for canonical EVA wet-cage logistics and recovery. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class EvaLogisticsCommands
{
    private EvaLogisticsCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("seele")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("eva")
                        .then(Commands.literal("status")
                                .executes(context -> status(context.getSource(), "all"))
                                .then(Commands.argument("variant", StringArgumentType.word())
                                        .executes(context -> status(context.getSource(),
                                                StringArgumentType.getString(context, "variant")))))
                        .then(Commands.literal("prepare")
                                .then(Commands.argument("variant", StringArgumentType.word())
                                        .executes(context -> prepare(context.getSource(),
                                                StringArgumentType.getString(context, "variant")))))
                        .then(Commands.literal("reset")
                                .then(Commands.argument("variant", StringArgumentType.word())
                                        .executes(context -> reset(context.getSource(),
                                                StringArgumentType.getString(context, "variant")))))
                        .then(Commands.literal("dummy")
                                .then(Commands.literal("start")
                                        .then(Commands.argument("variant", StringArgumentType.word())
                                                .executes(context -> dummyStart(
                                                        context.getSource(),
                                                        StringArgumentType.getString(context, "variant")))))
                                .then(Commands.literal("stop")
                                        .then(Commands.argument("variant", StringArgumentType.word())
                                                .executes(context -> dummyStop(
                                                        context.getSource(),
                                                        StringArgumentType.getString(context, "variant")))))
                                .then(Commands.literal("status")
                                        .executes(context -> dummyStatus(
                                                context.getSource())))))
                .then(Commands.literal("geofront")
                        .then(Commands.literal("hangar")
                                .executes(context -> enterHangar(context.getSource())))
                        .then(Commands.literal("recovery_control")
                                .executes(context -> enterRecoveryControl(
                                        context.getSource())))));
    }

    private static int status(CommandSourceStack source, String raw)
            throws CommandSyntaxException
    {
        ServerLevel level = geoFront(source);
        int requested = parseVariant(raw);
        int loaded = 0;
        for (int variant = 0; variant < 3; variant++)
        {
            if (requested >= 0 && requested != variant)
            {
                continue;
            }
            Status status = EvaLogisticsDirector.status(level, variant);
            if (status.loaded())
            {
                loaded++;
            }
            source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                    "EVA-%02d phase=%s loaded=%s canonical=%s LCL=%d/%d ticks=%d",
                    status.variant(), status.phase(), status.loaded(),
                    status.canonicalId() == null ? "none" : status.canonicalId(),
                    status.lclLayers(), EvaHangarBuilder.LCL_SHOULDER_LAYERS,
                    status.ticks())), false);
        }
        return loaded;
    }

    private static int prepare(CommandSourceStack source, String raw)
            throws CommandSyntaxException
    {
        ServerLevel level = geoFront(source);
        int requested = parseVariant(raw);
        int accepted = 0;
        for (int variant = 0; variant < 3; variant++)
        {
            if (requested >= 0 && requested != variant)
            {
                continue;
            }
            ActionResult result =
                    EvaLogisticsDirector.requestPrepare(level, variant);
            int current = variant;
            source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                    "EVA-%02d: %s", current, result.message())), false);
            if (result.accepted())
            {
                accepted++;
            }
        }
        return accepted;
    }

    private static int reset(CommandSourceStack source, String raw)
            throws CommandSyntaxException
    {
        ServerLevel level = geoFront(source);
        EvaHangarBuilder.ensure(level, IntegratedNervMapBuilder.GEOFRONT_ORIGIN);
        int requested = parseVariant(raw);
        int reset = 0;
        for (int variant = 0; variant < 3; variant++)
        {
            if (requested >= 0 && requested != variant)
            {
                continue;
            }
            EvaUnit01Entity unit = EvaLogisticsDirector.forceReset(level, variant);
            int current = variant;
            source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                    "EVA-%02d canonical airframe reset to wet cage: %s",
                    current, unit.getStringUUID())), false);
            reset++;
        }
        return reset;
    }

    private static int dummyStart(CommandSourceStack source, String raw)
            throws CommandSyntaxException
    {
        ServerLevel level = geoFront(source);
        int variant = parseVariant(raw);
        if (variant < 0)
        {
            throw new IllegalArgumentException(
                    "Start one dummy at a time: unit00, unit01 or unit02.");
        }
        TrainingPilotDirector.ActionResult result =
                TrainingPilotDirector.start(level, variant);
        source.sendSuccess(() -> Component.literal(result.message()), false);
        return result.accepted() ? 1 : 0;
    }

    private static int dummyStop(CommandSourceStack source, String raw)
            throws CommandSyntaxException
    {
        ServerLevel level = geoFront(source);
        int removed = TrainingPilotDirector.stop(level, parseVariant(raw));
        source.sendSuccess(() -> Component.literal(
                "Removed " + removed + " NERV training pilot(s)."), false);
        return removed;
    }

    private static int dummyStatus(CommandSourceStack source)
            throws CommandSyntaxException
    {
        ServerLevel level = geoFront(source);
        int count = 0;
        for (com.projectseele.entity.TrainingPilotEntity pilot
                : TrainingPilotDirector.pilots(level))
        {
            source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                    "DUMMY EVA-%02d stage=%s vehicle=%s position=%s",
                    pilot.getAssignedVariant(),
                    pilot.getTrainingStage()
                            == com.projectseele.entity.TrainingPilotEntity.STAGE_LINKED
                            ? "LINKED" : "WALKING",
                    pilot.getVehicle() == null ? "none"
                            : pilot.getVehicle().getStringUUID(),
                    pilot.blockPosition().toShortString())), false);
            count++;
        }
        if (count == 0)
        {
            source.sendSuccess(() -> Component.literal(
                    "No NERV training pilots are active."), false);
        }
        return count;
    }

    private static int enterHangar(CommandSourceStack source)
            throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(source);
        IntegratedNervMapBuilder.prepareRuntime(level);
        EvaLogisticsDirector.ensureFleet(level);
        BlockPos target = IntegratedNervMapBuilder.GEOFRONT_ORIGIN.offset(
                0, EvaHangarBuilder.GALLERY_Y + 1,
                EvaHangarBuilder.GALLERY_Z - 1);
        player.stopRiding();
        player.teleportTo(level, target.getX() + 0.5D, target.getY(),
                target.getZ() + 0.5D, 0.0F, 4.0F);
        source.sendSuccess(() -> Component.literal(
                "Entered NERV EVA wet-cage observation and logistics gallery."), false);
        return 1;
    }

    private static int enterRecoveryControl(CommandSourceStack source)
            throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(source);
        IntegratedNervMapBuilder.prepareRuntime(level);
        BlockPos target = Tokyo3RecoveryConsole.entryPosition(
                IntegratedNervMapBuilder.TOKYO3_ORIGIN);
        player.stopRiding();
        player.teleportTo(level, target.getX() + 0.5D, target.getY(),
                target.getZ() + 0.5D, 180.0F, 0.0F);
        source.sendSuccess(() -> Component.literal(
                "Entered Tokyo-3 surface recovery command post."), false);
        return 1;
    }
    private static ServerLevel geoFront(CommandSourceStack source)
            throws CommandSyntaxException
    {
        ServerLevel level = source.getServer().getLevel(GeoFrontCommands.GEOFRONT);
        if (level == null)
        {
            throw new IllegalStateException("GeoFront dimension is unavailable");
        }
        return level;
    }

    /** Returns -1 for all. */
    private static int parseVariant(String raw)
    {
        String normalized = raw.toLowerCase(Locale.ROOT)
                .replace("eva", "").replace("unit", "")
                .replace("-", "").replace("_", "");
        return switch (normalized)
        {
            case "all", "fleet" -> -1;
            case "0", "00", "rei" -> 0;
            case "1", "01", "shinji" -> 1;
            case "2", "02", "asuka" -> 2;
            default -> throw new IllegalArgumentException(
                    "Variant must be unit00, unit01, unit02 or all.");
        };
    }
}
