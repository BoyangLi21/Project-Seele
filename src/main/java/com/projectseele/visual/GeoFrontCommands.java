package com.projectseele.visual;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
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
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
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
    private static final Set<UUID> VISUAL_SORTIE_UNITS = new HashSet<>();
    private static boolean visualLinkInProgress;

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
                        .then(Commands.literal("link")
                                .executes(context -> link(context.getSource())))
                        .then(Commands.literal("sortie_audit")
                                .executes(context -> sortieAudit(context.getSource())))
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

    /**
     * Moves the three parked EVAs from one audited surface complex onto the
     * matching GeoFront terminals and preserves each exact surface bed as its
     * next sortie destination.
     */
    static int link(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        if (player.isPassenger())
        {
            source.sendFailure(Component.literal(
                    "Dismount before linking the GeoFront sortie terminals."));
            return 0;
        }
        if (player.serverLevel().dimension().equals(GEOFRONT))
        {
            source.sendFailure(Component.literal(
                    "Run /seele geofront link beside the surface launch complex."));
            return 0;
        }

        ServerLevel surface = player.serverLevel();
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        GeoFrontBuilder.build(geoFront, ORIGIN);
        GeoFrontAudit mapAudit = GeoFrontBuilder.inspect(geoFront, ORIGIN);
        if (!mapAudit.valid())
        {
            source.sendFailure(Component.literal(
                    "GeoFront failed its map audit: " + mapAudit.summary()));
            return 0;
        }

        EvaUnit01Entity centreUnit = surface.getEntitiesOfClass(EvaUnit01Entity.class,
                player.getBoundingBox().inflate(240.0D, 128.0D, 240.0D),
                unit -> unit.isAlive()
                        && unit.getUnitVariant() == EvaUnit01Entity.UNIT_01
                        && unit.findLaunchBed() != null).stream()
                .min((left, right) -> Double.compare(
                        left.distanceToSqr(player), right.distanceToSqr(player)))
                .orElse(null);
        if (centreUnit == null || centreUnit.findLaunchBed() == null)
        {
            source.sendFailure(Component.literal(
                    "No parked Unit-01 launch bay found within 240 blocks."));
            return 0;
        }
        BlockPos centreBed = centreUnit.findLaunchBed();
        List<EvaUnit01Entity> surfaceUnits = surface.getEntitiesOfClass(
                EvaUnit01Entity.class, new AABB(centreBed).inflate(48.0D, 40.0D, 48.0D),
                unit -> unit.isAlive() && unit.findLaunchBed() != null
                        && !unit.isVehicle() && !unit.isLaunchSequenceActive());
        if (!hasAllVariants(surfaceUnits) || surfaceUnits.size() != 3)
        {
            source.sendFailure(Component.literal(
                    "Surface complex must contain exactly one parked Unit-00, 01 and 02."));
            return 0;
        }

        AABB terminalArea = new AABB(ORIGIN)
                .inflate(GeoFrontBuilder.CAVERN_RADIUS, 96.0D,
                        GeoFrontBuilder.CAVERN_RADIUS);
        if (!geoFront.getEntitiesOfClass(EvaUnit01Entity.class, terminalArea,
                unit -> unit.isAlive()).isEmpty())
        {
            source.sendFailure(Component.literal(
                    "GeoFront terminals are already occupied; audit the existing sortie first."));
            return 0;
        }

        saveReturn(player);
        List<LinkedUnit> moved = new ArrayList<>();
        for (EvaUnit01Entity unit : surfaceUnits)
        {
            BlockPos surfaceBed = unit.findLaunchBed();
            int liftX = liftX(unit.getUnitVariant());
            BlockPos terminalBed = ORIGIN.offset(liftX, 1, -76);
            unit.setSortieDestination(surface.dimension(), surfaceBed);
            EvaUnit01Entity relocated = unit.transferUnpilotedTo(geoFront,
                    Vec3.atBottomCenterOf(terminalBed.above()),
                    EvaUnit01Entity.SILO_BAY_YAW);
            if (relocated == null)
            {
                unit.clearSortieDestination();
                rollbackLinks(surface, moved);
                source.sendFailure(Component.literal(
                        "A dimension-transfer hook rejected the EVA link; previous moves were rolled back."));
                return 0;
            }
            relocated.setSortieParkingBed(terminalBed);
            moved.add(new LinkedUnit(relocated, surfaceBed));
        }

        if (visualLinkInProgress)
        {
            VISUAL_SORTIE_UNITS.clear();
            moved.forEach(link -> VISUAL_SORTIE_UNITS.add(link.unit().getUUID()));
        }

        SortieAudit result = inspectLinkedUnits(player.getServer(), geoFront,
                moved.stream().map(LinkedUnit::unit).toList());
        logSortieAudit("link", result);
        if (!result.valid())
        {
            rollbackLinks(surface, moved);
            source.sendFailure(Component.literal(
                    "GeoFront sortie link failed audit and was rolled back: " + result.summary()));
            return 0;
        }

        BlockPos centralTerminal = ORIGIN.offset(0, 1, -76);
        player.teleportTo(geoFront, centralTerminal.getX() + 0.5D,
                centralTerminal.getY() + 27.0D,
                centralTerminal.getZ() + 6.5D, 180.0F, -8.0F);
        source.sendSuccess(() -> Component.literal(
                "GeoFront sortie linked: Unit-00/01/02 are underground. "
                        + "Use the dorsal plug or /seele silo board; launch exits at Tokyo-3."), false);
        return 1;
    }

    /** Dedicated-world reset before the unattended cross-dimension sortie. */
    static void preloadVisualSortie(ServerPlayer player)
    {
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            throw new IllegalStateException("GeoFront visual sortie dimension is unavailable");
        }
        GeoFrontBuilder.build(geoFront, ORIGIN);
        loadCavernChunks(geoFront);
        player.stopRiding();
        player.teleportTo(geoFront,
                ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + GeoFrontBuilder.OBSERVATION_Y + 1.0D,
                ORIGIN.getZ() + GeoFrontBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 0.0F);
        ProjectSeele.LOGGER.info(
                "Visual GeoFront sortie preloaded the complete cavern entity region "
                        + "and entered it to activate persistent entities");
    }

    /** Dedicated-world reset before the unattended cross-dimension sortie. */
    static int linkVisualCapture(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            throw new IllegalStateException("GeoFront visual sortie dimension is unavailable");
        }
        int staleUnits = clearVisualSortieEntities(geoFront);
        ProjectSeele.LOGGER.info(
                "Visual GeoFront sortie cleanup removed {} persistent EVA entities",
                staleUnits);
        player.teleportTo(player.getServer().overworld(),
                0.5D, 97.0D, 0.5D, 180.0F, 0.0F);
        visualLinkInProgress = true;
        try
        {
            return link(player.createCommandSourceStack());
        }
        finally
        {
            visualLinkInProgress = false;
        }
    }

    /**
     * Loads every cavern chunk before querying entities. An EVA frozen in an
     * unloaded chunk is absent from ordinary AABB queries, but is restored as
     * soon as its parking chunk loads; that used to contaminate later visual
     * runs with duplicate airframes.
     */
    private static int clearVisualSortieEntities(ServerLevel geoFront)
    {
        loadCavernChunks(geoFront);

        List<EvaUnit01Entity> stale = geoFront.getEntitiesOfClass(
                EvaUnit01Entity.class,
                new AABB(ORIGIN).inflate(GeoFrontBuilder.CAVERN_RADIUS + 32.0D,
                        192.0D, GeoFrontBuilder.CAVERN_RADIUS + 32.0D));
        stale.forEach(EvaUnit01Entity::discard);
        return stale.size();
    }

    private static void loadCavernChunks(ServerLevel geoFront)
    {
        int chunkRadius = (GeoFrontBuilder.CAVERN_RADIUS >> 4) + 2;
        int originChunkX = ORIGIN.getX() >> 4;
        int originChunkZ = ORIGIN.getZ() >> 4;
        for (int chunkX = originChunkX - chunkRadius;
             chunkX <= originChunkX + chunkRadius; chunkX++)
        {
            for (int chunkZ = originChunkZ - chunkRadius;
                 chunkZ <= originChunkZ + chunkRadius; chunkZ++)
            {
                geoFront.getChunk(chunkX, chunkZ);
            }
        }
    }

    private static int sortieAudit(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            return 0;
        }
        SortieAudit result = inspectSortie(player.getServer(), geoFront);
        logSortieAudit("command", result);
        Component report = Component.literal(result.summary());
        if (result.valid())
        {
            source.sendSuccess(() -> report, false);
            return 1;
        }
        source.sendFailure(report);
        return 0;
    }

    static SortieAudit inspectSortie(net.minecraft.server.MinecraftServer server,
                                     ServerLevel geoFront)
    {
        List<EvaUnit01Entity> units = geoFront.getEntitiesOfClass(EvaUnit01Entity.class,
                new AABB(ORIGIN.offset(0, 1, -76)).inflate(48.0D, 40.0D, 20.0D),
                unit -> unit.isAlive() && unit.findLaunchBed() != null);
        return inspectLinkedUnits(server, geoFront, units);
    }

    private static SortieAudit inspectLinkedUnits(
            net.minecraft.server.MinecraftServer server,
            ServerLevel geoFront, List<EvaUnit01Entity> units)
    {
        int linked = 0;
        int validDestinations = 0;
        for (EvaUnit01Entity unit : units)
        {
            if (!unit.hasSortieDestination())
            {
                continue;
            }
            linked++;
            ServerLevel destination = server.getLevel(unit.getSortieDestinationDimension());
            BlockPos bed = unit.getSortieDestinationBed();
            if (destination != null && bed != null
                    && destination.getBlockState(bed).is(
                            net.minecraft.world.level.block.Blocks.LODESTONE))
            {
                validDestinations++;
            }
        }
        boolean variants = hasAllVariants(units);
        boolean gantries = GeoFrontBuilder.inspect(geoFront, ORIGIN).gantries() == 3;
        boolean valid = units.size() == 3 && linked == 3 && validDestinations == 3
                && variants && gantries;
        return new SortieAudit(valid, units.size(), linked, validDestinations,
                variants, gantries);
    }

    /** Removes persistent entities from earlier unattended runs after the
     * destination dimension has activated its entity index. */
    static int pruneVisualSortieDuplicates(ServerLevel geoFront)
    {
        if (VISUAL_SORTIE_UNITS.size() != 3)
        {
            throw new IllegalStateException(
                    "Visual GeoFront sortie did not retain exactly three linked UUIDs");
        }
        List<EvaUnit01Entity> loaded = geoFront.getEntitiesOfClass(
                EvaUnit01Entity.class,
                new AABB(ORIGIN).inflate(GeoFrontBuilder.CAVERN_RADIUS + 32.0D,
                        192.0D, GeoFrontBuilder.CAVERN_RADIUS + 32.0D));
        int removed = 0;
        for (EvaUnit01Entity unit : loaded)
        {
            if (!VISUAL_SORTIE_UNITS.contains(unit.getUUID()))
            {
                unit.discard();
                removed++;
            }
        }
        ProjectSeele.LOGGER.info(
                "Visual GeoFront sortie retained 3 linked UUIDs and removed {} stale entities",
                removed);
        return removed;
    }

    private static boolean hasAllVariants(List<EvaUnit01Entity> units)
    {
        boolean has00 = units.stream().anyMatch(
                unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_00);
        boolean has01 = units.stream().anyMatch(
                unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_01);
        boolean has02 = units.stream().anyMatch(
                unit -> unit.getUnitVariant() == EvaUnit01Entity.UNIT_02);
        return has00 && has01 && has02;
    }

    private static int liftX(int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> -28;
            case EvaUnit01Entity.UNIT_02 -> 28;
            default -> 0;
        };
    }

    private static void rollbackLinks(ServerLevel surface, List<LinkedUnit> moved)
    {
        for (LinkedUnit link : moved)
        {
            link.unit().clearSortieDestination();
            EvaUnit01Entity restored = link.unit().transferUnpilotedTo(surface,
                    Vec3.atBottomCenterOf(link.surfaceBed().above()),
                    EvaUnit01Entity.SILO_BAY_YAW);
            if (restored == null)
            {
                ProjectSeele.LOGGER.error(
                        "NERV sortie rollback failed: eva={} bed={}",
                        link.unit().getStringUUID(), link.surfaceBed().toShortString());
            }
        }
    }

    private static void logSortieAudit(String stage, SortieAudit result)
    {
        if (result.valid())
        {
            ProjectSeele.LOGGER.info("GeoFront sortie audit [{}]: {}", stage, result.summary());
        }
        else
        {
            ProjectSeele.LOGGER.error("GEOFRONT SORTIE INVALID [{}]: {}", stage,
                    result.summary());
        }
    }

    private record LinkedUnit(EvaUnit01Entity unit, BlockPos surfaceBed) {}

    static record SortieAudit(boolean valid, int units, int linked,
                              int destinations, boolean variants, boolean gantries)
    {
        String summary()
        {
            return String.format(Locale.ROOT,
                    "valid=%s units=%d linked=%d destinations=%d/3 "
                            + "variants00/01/02=%s gantries=%s",
                    this.valid, this.units, this.linked, this.destinations,
                    this.variants, this.gantries);
        }
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
