package com.projectseele.visual;

import java.util.Arrays;
import java.util.Locale;
import java.util.Optional;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.ServerboundEvaVideoFramePacket;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.NervCommandTelemetry;
import com.projectseele.world.NervCrewSavedData;
import com.projectseele.world.NervCrewSavedData.Assignment;
import com.projectseele.world.NervCrewSavedData.ClaimResult;
import com.projectseele.world.NervCrewSavedData.CrewOverview;
import com.projectseele.world.NervCrewSavedData.Station;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Player-facing NERV crew coordination and operator server diagnostics. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class NervCrewCommands
{
    private static final String[] STATION_IDS = Arrays.stream(Station.values())
            .map(Station::id).toArray(String[]::new);

    private NervCrewCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("nerv")
                .executes(context -> crewStatus(context.getSource()))
                .then(Commands.literal("crew")
                        .executes(context -> crewStatus(context.getSource()))
                        .then(Commands.literal("status")
                                .executes(context -> crewStatus(context.getSource())))
                        .then(Commands.literal("claim")
                                .then(Commands.argument("station", StringArgumentType.word())
                                        .suggests((context, builder) ->
                                                SharedSuggestionProvider.suggest(
                                                        STATION_IDS, builder))
                                        .executes(context -> claim(
                                                context.getSource(),
                                                StringArgumentType.getString(
                                                        context, "station")))))
                        .then(Commands.literal("ready")
                                .executes(context -> ready(context.getSource(), true)))
                        .then(Commands.literal("standby")
                                .executes(context -> ready(context.getSource(), false)))
                        .then(Commands.literal("release")
                                .executes(context -> release(context.getSource())))
                        .then(Commands.literal("clear")
                                .requires(source -> source.hasPermission(2))
                                .then(Commands.argument("station", StringArgumentType.word())
                                        .suggests((context, builder) ->
                                                SharedSuggestionProvider.suggest(
                                                        STATION_IDS, builder))
                                        .executes(context -> clear(
                                                context.getSource(),
                                                StringArgumentType.getString(
                                                        context, "station"))))))
                .then(Commands.literal("server")
                        .then(Commands.literal("status")
                                .executes(context -> serverStatus(context.getSource())))
                        .then(Commands.literal("audit")
                                .requires(source -> source.hasPermission(2))
                                .executes(context -> serverAudit(context.getSource())))));

        // Operator alias under the existing permission-gated SEELE tree.
        dispatcher.register(Commands.literal("seele")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("server")
                        .executes(context -> serverStatus(context.getSource()))
                        .then(Commands.literal("status")
                                .executes(context -> serverStatus(context.getSource())))
                        .then(Commands.literal("audit")
                                .executes(context -> serverAudit(context.getSource())))));
    }

    @SubscribeEvent
    public static void onPlayerLoggedIn(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (!(event.getEntity() instanceof ServerPlayer player))
        {
            return;
        }
        NervCrewSavedData data = NervCrewSavedData.get(player.server);
        data.stationFor(player.getUUID()).ifPresent(station ->
        {
            boolean ready = data.assignment(station)
                    .map(Assignment::ready).orElse(false);
            player.displayClientMessage(Component.literal(
                    "NERV CREW / " + station.label() + " / "
                            + (ready ? "READY" : "STANDBY")
                            + "  (/nerv crew status)")
                    .withStyle(ready ? ChatFormatting.GREEN
                            : ChatFormatting.GOLD), false);
        });
    }

    private static int claim(CommandSourceStack source, String raw)
            throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        Optional<Station> parsed = Station.parse(raw);
        if (parsed.isEmpty())
        {
            source.sendFailure(Component.literal(
                    "Unknown NERV station. Use: "
                            + String.join(", ", STATION_IDS)));
            return 0;
        }
        NervCrewSavedData data = NervCrewSavedData.get(source.getServer());
        Station station = parsed.get();
        ClaimResult result = data.claim(station, player);
        if (result == ClaimResult.OCCUPIED)
        {
            String owner = data.assignment(station)
                    .map(Assignment::playerName).orElse("UNKNOWN");
            source.sendFailure(Component.literal(station.label()
                    + " is reserved by " + owner
                    + ". Ask an operator to clear it if stale."));
            return 0;
        }
        source.sendSuccess(() -> Component.literal(
                result == ClaimResult.ALREADY_ASSIGNED
                        ? "NERV station retained: " + station.label()
                        : "NERV station claimed: " + station.label()
                                + ". Set /nerv crew ready when prepared."), false);
        return 1;
    }

    private static int ready(CommandSourceStack source, boolean ready)
            throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        NervCrewSavedData data = NervCrewSavedData.get(source.getServer());
        if (!data.setReady(player.getUUID(), ready))
        {
            source.sendFailure(Component.literal(
                    "Claim a station first: /nerv crew claim <station>"));
            return 0;
        }
        Station station = data.stationFor(player.getUUID()).orElseThrow();
        source.sendSuccess(() -> Component.literal("NERV " + station.label()
                        + " -> " + (ready ? "READY" : "STANDBY"))
                .withStyle(ready ? ChatFormatting.GREEN
                        : ChatFormatting.GOLD), false);
        return 1;
    }

    private static int release(CommandSourceStack source)
            throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        Optional<Station> released = NervCrewSavedData.get(source.getServer())
                .release(player.getUUID());
        if (released.isEmpty())
        {
            source.sendFailure(Component.literal("No NERV station is assigned."));
            return 0;
        }
        source.sendSuccess(() -> Component.literal(
                "NERV station released: " + released.get().label()), false);
        return 1;
    }

    private static int clear(CommandSourceStack source, String raw)
    {
        Optional<Station> parsed = Station.parse(raw);
        if (parsed.isEmpty())
        {
            source.sendFailure(Component.literal(
                    "Unknown NERV station. Use: "
                            + String.join(", ", STATION_IDS)));
            return 0;
        }
        Optional<Assignment> removed = NervCrewSavedData.get(source.getServer())
                .clear(parsed.get());
        if (removed.isEmpty())
        {
            source.sendFailure(Component.literal(parsed.get().label()
                    + " is already unassigned."));
            return 0;
        }
        source.sendSuccess(() -> Component.literal("Cleared "
                + parsed.get().label() + " assignment for "
                + removed.get().playerName()), true);
        return 1;
    }

    private static int crewStatus(CommandSourceStack source)
    {
        MinecraftServer server = source.getServer();
        NervCrewSavedData data = NervCrewSavedData.get(server);
        CrewOverview overview = data.overview(server);
        source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                        "NERV CREW / assigned %d/6 / online %d / ready %d / online-ready %d",
                        overview.assigned(), overview.online(), overview.ready(),
                        overview.onlineReady()))
                .withStyle(overview.allAssignedOnlineReady()
                        ? ChatFormatting.GREEN : ChatFormatting.GOLD), false);
        for (Station station : Station.values())
        {
            Optional<Assignment> assignment = data.assignment(station);
            String line;
            ChatFormatting colour;
            if (assignment.isEmpty())
            {
                line = String.format(Locale.ROOT, "%-10s [OPEN]", station.shortLabel());
                colour = ChatFormatting.DARK_GRAY;
            }
            else
            {
                Assignment value = assignment.get();
                boolean online = server.getPlayerList()
                        .getPlayer(value.playerId()) != null;
                line = String.format(Locale.ROOT, "%-10s %-16s %s / %s",
                        station.shortLabel(), value.playerName(),
                        online ? "ONLINE" : "OFFLINE",
                        value.ready() ? "READY" : "STANDBY");
                colour = !online ? ChatFormatting.DARK_RED
                        : value.ready() ? ChatFormatting.GREEN
                        : ChatFormatting.YELLOW;
            }
            ChatFormatting finalColour = colour;
            source.sendSuccess(() -> Component.literal(line)
                    .withStyle(finalColour), false);
        }
        return overview.assigned();
    }

    private static int serverStatus(CommandSourceStack source)
    {
        MinecraftServer server = source.getServer();
        ServerLevel level = server.getLevel(GeoFrontCommands.GEOFRONT);
        source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                        "PROJECT SEELE SERVER / %s / players %d/%d",
                        server.isDedicatedServer() ? "DEDICATED" : "INTEGRATED",
                        server.getPlayerCount(), server.getMaxPlayers()))
                .withStyle(ChatFormatting.GOLD), false);
        if (level == null)
        {
            source.sendFailure(Component.literal(
                    "GeoFront dimension is unavailable; verify the mod and datapack load."));
            return 0;
        }
        boolean installed = IntegratedNervMapBuilder.isInstalled(level);
        AABB area = new AABB(
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN.getX() - 360.0D,
                level.getMinBuildHeight(),
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN.getZ() - 360.0D,
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN.getX() + 360.0D,
                level.getMaxBuildHeight(),
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN.getZ() + 360.0D);
        int airframes = level.getEntitiesOfClass(EvaUnit01Entity.class, area,
                Entity::isAlive).size();
        int screens = installed ? NervCommandTelemetry.countScreens(level,
                IntegratedNervMapBuilder.GEOFRONT_ORIGIN) : 0;
        int feeds = 0;
        for (int variant = EvaUnit01Entity.UNIT_00;
             variant <= EvaUnit01Entity.UNIT_02; variant++)
        {
            if (ServerboundEvaVideoFramePacket.isFeedActive(level, variant))
            {
                feeds++;
            }
        }
        CrewOverview crew = NervCrewSavedData.get(server).overview(server);
        boolean finalInstalled = installed;
        int finalFeeds = feeds;
        source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                        "MAP %s / loaded EVA %d/3 / telemetry %d/%d / cockpit feeds %d/3",
                        finalInstalled ? "CONNECTED" : "MISSING",
                        airframes, screens, NervCommandTelemetry.SCREEN_COUNT,
                        finalFeeds))
                .withStyle(finalInstalled ? ChatFormatting.GREEN
                        : ChatFormatting.RED), false);
        source.sendSuccess(() -> Component.literal(String.format(Locale.ROOT,
                        "CREW assigned %d/6 / online %d / online-ready %d",
                        crew.assigned(), crew.online(), crew.onlineReady()))
                .withStyle(crew.allAssignedOnlineReady()
                        ? ChatFormatting.GREEN : ChatFormatting.YELLOW), false);
        source.sendSuccess(() -> Component.literal(
                "Use /nerv server audit for the bounded sortie gate; it never rebuilds the full map.")
                .withStyle(ChatFormatting.GRAY), false);
        return installed ? 1 : 0;
    }

    private static int serverAudit(CommandSourceStack source)
    {
        ServerLevel level = source.getServer().getLevel(GeoFrontCommands.GEOFRONT);
        if (level == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        IntegratedNervMapBuilder.RuntimeAudit audit =
                IntegratedNervMapBuilder.prepareRuntime(level);
        if (!audit.valid())
        {
            source.sendFailure(Component.literal(
                    "NERV runtime gate FAILED: " + audit.summary()));
            return 0;
        }
        source.sendSuccess(() -> Component.literal(
                        "NERV runtime gate READY: " + audit.summary())
                .withStyle(ChatFormatting.GREEN), true);
        return 1;
    }
}
