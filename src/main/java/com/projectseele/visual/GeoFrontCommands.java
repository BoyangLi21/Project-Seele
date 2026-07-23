package com.projectseele.visual;

import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.GeoFrontBuilder;
import com.projectseele.world.EvaLogisticsDirector;
import com.projectseele.world.GeoFrontBuilder.GeoFrontAudit;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.IntegratedNervMapBuilder.IntegratedAudit;
import com.projectseele.world.IntegratedNervMapBuilder.LiftLink;
import com.projectseele.world.LocalMapAssetLoader;
import com.projectseele.world.NervOperationsCentreBuilder;
import com.projectseele.world.TerminalDogmaBuilder;
import com.projectseele.world.ThirdTokyoSurfaceBuilder;
import com.projectseele.world.Tokyo3RetractionDirector;
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
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Builds and operates the physically continuous Tokyo-3 / GeoFront world. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class GeoFrontCommands
{
    public static final ResourceKey<Level> GEOFRONT = ResourceKey.create(
            Registries.DIMENSION,
            new ResourceLocation(ProjectSeele.MODID, "geofront"));
    public static final BlockPos ORIGIN = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
    public static final BlockPos TOKYO3_ORIGIN = IntegratedNervMapBuilder.TOKYO3_ORIGIN;

    private static final String RETURN_DIMENSION = "SeeleGeoFrontReturnDimension";
    private static final String RETURN_X = "SeeleGeoFrontReturnX";
    private static final String RETURN_Y = "SeeleGeoFrontReturnY";
    private static final String RETURN_Z = "SeeleGeoFrontReturnZ";
    private static final int SORTIE_CHUNK_RADIUS = 4;
    private static final double SORTIE_ENTITY_RADIUS = 72.0D;
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
                        .then(Commands.literal("exit")
                                .executes(context -> exit(context.getSource())))
                        .then(Commands.literal("audit")
                                .executes(context -> audit(context.getSource())))
                        .then(Commands.literal("operations")
                                .executes(context -> operations(context.getSource())))
                        .then(Commands.literal("dogma")
                                .executes(context -> dogma(context.getSource())))
                        .then(Commands.literal("overview")
                                .executes(context -> overview(context.getSource())))));
    }

    /**
     * The private evaluation save is copied from an empty Visual Lab template.
     * Its inherited overworld player position sits four blocks above the world
     * minimum, so a first manual login can fall before the user runs setup.
     */
    @SubscribeEvent
    public static void rescueStagedWorldLogin(PlayerEvent.PlayerLoggedInEvent event)
    {
        if (!(event.getEntity() instanceof ServerPlayer player))
        {
            return;
        }
        ServerLevel current = player.serverLevel();
        ServerLevel installedMap = current.dimension().equals(GEOFRONT)
                ? current : current.getServer().getLevel(GEOFRONT);
        if (installedMap != null
                && IntegratedNervMapBuilder.isInstalled(installedMap))
        {
            IntegratedNervMapBuilder.RuntimeAudit runtime =
                    IntegratedNervMapBuilder.prepareRuntime(installedMap);
            if (!runtime.valid())
            {
                ProjectSeele.LOGGER.warn(
                        "GeoFront login infrastructure gate needs operator repair: {}",
                        runtime.summary());
            }
        }
        if (unsafeOverviewLogin(player, current))
        {
            teleportOverview(player, current);
            ProjectSeele.LOGGER.info(
                    "Rescued {} from an unsafe saved GeoFront overview position",
                    player.getGameProfile().getName());
            return;
        }
        if (!current.dimension().equals(Level.OVERWORLD)
                || !LocalMapAssetLoader.stagedEvaWorld(current)
                || player.getY() > current.getMinBuildHeight() + 8.0D)
        {
            return;
        }
        ServerLevel destination = geoFront(player);
        if (destination == null)
        {
            ProjectSeele.LOGGER.error(
                    "Staged Tokyo-3 login rescue failed: GeoFront dimension is unavailable");
            return;
        }
        if (!IntegratedNervMapBuilder.isInstalled(destination))
        {
            IntegratedAudit audit = IntegratedNervMapBuilder.ensure(destination);
            if (!audit.valid())
            {
                ProjectSeele.LOGGER.error(
                        "Staged Tokyo-3 login rescue refused an invalid connected map: {}",
                        audit.summary());
                return;
            }
        }
        prepareSurfaceLanding(destination);
        player.teleportTo(destination,
                TOKYO3_ORIGIN.getX() + 0.5D,
                TOKYO3_ORIGIN.getY() + ThirdTokyoSurfaceBuilder.OBSERVATION_Y + 1.0D,
                TOKYO3_ORIGIN.getZ() + ThirdTokyoSurfaceBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 18.0F);
        ProjectSeele.LOGGER.info(
                "Rescued staged-world player {} from the empty template spawn to Tokyo-3",
                player.getGameProfile().getName());
    }

    static int setup(CommandSourceStack source) throws CommandSyntaxException
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
        IntegratedAudit result = IntegratedNervMapBuilder.ensure(level);
        Tokyo3RetractionDirector.register(level, TOKYO3_ORIGIN);
        logIntegratedAudit("setup", result);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(
                    "The connected Tokyo-3 / GeoFront map failed audit: "
                            + result.summary()));
            return 0;
        }
        teleportOverview(player, level);
        source.sendSuccess(() -> Component.literal(
                "Connected Tokyo-3 / GeoFront map ready: three physical "
                        + IntegratedNervMapBuilder.ascentDistance() + "-block shafts. "
                        + "Run /seele geofront link to prepare Unit-00/01/02."),
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
        // A previous manual session may have saved the automation player in
        // Unit-01.  Release that stale passenger relation before the strict
        // three-airframe canonicalization gate runs.
        player.stopRiding();
        level.setDayTime(6000L);
        level.setWeatherParameters(12000, 0, false, false);
        // Visual captures must not inherit a CITY ARMOUR state left by a
        // previous manual session. Restore the physical tower volumes before
        // the fixed-camera audit; changing SavedData alone can leave a valid
        // looking marker set above an empty skyline.
        Tokyo3RetractionDirector.forceDepth(level,
                IntegratedNervMapBuilder.TOKYO3_ORIGIN, false);
        IntegratedAudit result = IntegratedNervMapBuilder.ensure(level);
        logIntegratedAudit("visual-setup", result);
        if (!result.valid())
        {
            throw new IllegalStateException(
                    "Integrated GeoFront visual setup failed audit: " + result.summary());
        }
        List<EvaUnit01Entity> linked = ensureContinuousSortieUnits(level);
        SortieAudit sortie = inspectLinkedUnits(player.getServer(), level, linked);
        if (!sortie.valid())
        {
            // Unattended captures are a destructive development fixture, not
            // a player command. Recover all three canonical units when an old
            // run left one deployed or its UUID in another dimension; normal
            // login and readiness checks continue to preserve deployed EVAs.
            ProjectSeele.LOGGER.warn(
                    "Visual GeoFront fixture repairing incomplete fleet: {}",
                    sortie.summary());
            for (int variant = 0; variant < 3; variant++)
            {
                EvaLogisticsDirector.forceReset(level, variant);
            }
            linked = ensureContinuousSortieUnits(level);
            sortie = inspectLinkedUnits(player.getServer(), level, linked);
        }
        logSortieAudit("geofront-visual", sortie);
        if (!sortie.valid())
        {
            throw new IllegalStateException(
                    "GeoFront visual launch bays failed audit after canonical reset: "
                            + sortie.summary());
        }
        // Exercise the same public navigation paths used during manual QA.
        // This catches unsafe overview landings and operations-route audit
        // regressions before the client starts jumping between camera rigs.
        if (overview(source) != 1 || operations(source) != 1)
        {
            throw new IllegalStateException(
                    "GeoFront overview/operations navigation smoke test failed");
        }
        ProjectSeele.LOGGER.info(
                "GeoFront navigation smoke test passed: overview landing is dry and operations routes are valid");
        BlockPos hiddenPlatform = ORIGIN.offset(0, 3, 0);
        level.setBlock(hiddenPlatform, net.minecraft.world.level.block.Blocks.BARRIER
                .defaultBlockState(), net.minecraft.world.level.block.Block.UPDATE_CLIENTS);
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
        if (!IntegratedNervMapBuilder.isInstalled(level))
        {
            source.sendFailure(Component.literal(
                    "The connected map is not installed. "
                            + "Run /seele geofront setup first."));
            return 0;
        }
        saveReturn(player);
        teleportOverview(player, level);
        return 1;
    }

    /** Prepares three EVAs at the physical lower stations; no transfer occurs. */
    static int link(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        if (player.isPassenger())
        {
            source.sendFailure(Component.literal(
                    "Dismount before linking the GeoFront sortie terminals."));
            return 0;
        }
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        IntegratedNervMapBuilder.RuntimeAudit mapAudit =
                IntegratedNervMapBuilder.prepareRuntime(geoFront);
        Tokyo3RetractionDirector.register(geoFront, TOKYO3_ORIGIN);
        if (!mapAudit.valid())
        {
            source.sendFailure(Component.literal(
                    "Connected sortie route failed its runtime gate: "
                            + mapAudit.summary()));
            return 0;
        }
        List<EvaUnit01Entity> linked;
        try
        {
            linked = ensureContinuousSortieUnits(geoFront);
        }
        catch (IllegalStateException exception)
        {
            source.sendFailure(Component.literal(exception.getMessage()));
            return 0;
        }

        if (visualLinkInProgress)
        {
            VISUAL_SORTIE_UNITS.clear();
            linked.forEach(unit -> VISUAL_SORTIE_UNITS.add(unit.getUUID()));
        }

        SortieAudit result = inspectLinkedUnits(player.getServer(), geoFront,
                linked);
        logSortieAudit("link", result);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(
                    "Physical sortie link failed audit: " + result.summary()));
            return 0;
        }

        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        BlockPos centralTerminal = IntegratedNervMapBuilder.lowerLiftBed(1);
        player.teleportTo(geoFront, centralTerminal.getX() + 0.5D,
                centralTerminal.getY() + 27.0D,
                centralTerminal.getZ() + 6.5D, 180.0F, -8.0F);
        source.sendSuccess(() -> Component.literal(
                "Physical sortie ready: Unit-00/01/02 are registered in their individual wet cages. "
                        + "Launch travels the same "
                        + IntegratedNervMapBuilder.ascentDistance()
                        + "-block shaft into Tokyo-3; no portal or EVA teleport."), false);
        return 1;
    }

    public static List<EvaUnit01Entity> ensureContinuousSortieUnits(ServerLevel level)
    {
        return EvaLogisticsDirector.ensureFleet(level);
    }
    /** Dedicated-world reset before the unattended cross-dimension sortie. */
    static void preloadVisualSortie(ServerPlayer player)
    {
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            throw new IllegalStateException("GeoFront visual sortie dimension is unavailable");
        }
        IntegratedNervMapBuilder.RuntimeAudit audit =
                IntegratedNervMapBuilder.prepareRuntime(geoFront);
        if (!audit.valid())
        {
            throw new IllegalStateException(
                    "GeoFront visual sortie runtime gate failed: "
                            + audit.summary());
        }
        loadSortieChunks(geoFront);
        player.stopRiding();
        player.teleportTo(geoFront,
                ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + GeoFrontBuilder.OBSERVATION_Y + 1.0D,
                ORIGIN.getZ() + GeoFrontBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 0.0F);
        ProjectSeele.LOGGER.info(
                "Visual GeoFront sortie preloaded the three launch-bay chunk columns "
                        + "and entered them to activate persistent entities");
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

    /** Loads only the launch-bay neighbourhood before querying parked EVAs. */
    private static int clearVisualSortieEntities(ServerLevel geoFront)
    {
        loadSortieChunks(geoFront);

        BlockPos centre = IntegratedNervMapBuilder.lowerLiftBed(1);
        List<EvaUnit01Entity> stale = geoFront.getEntitiesOfClass(
                EvaUnit01Entity.class,
                new AABB(centre).inflate(SORTIE_ENTITY_RADIUS,
                        384.0D, SORTIE_ENTITY_RADIUS));
        // Reset through the fleet director so SavedData and the three new
        // UUIDs move together. Directly discarding entities leaves PARKED
        // canonical UUIDs pointing at nothing on the next launch.
        for (int variant = 0; variant < 3; variant++)
        {
            EvaLogisticsDirector.forceReset(geoFront, variant);
        }
        return stale.size();
    }

    private static void loadSortieChunks(ServerLevel geoFront)
    {
        BlockPos centre = IntegratedNervMapBuilder.lowerLiftBed(1);
        int originChunkX = centre.getX() >> 4;
        int originChunkZ = centre.getZ() >> 4;
        int chunkRadius = SORTIE_CHUNK_RADIUS;
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
        List<EvaUnit01Entity> units = EvaLogisticsDirector.ensureFleet(geoFront);
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
                new AABB(IntegratedNervMapBuilder.lowerLiftBed(1)).inflate(
                        SORTIE_ENTITY_RADIUS, 384.0D, SORTIE_ENTITY_RADIUS));
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
        ServerLevel destination = geoFront(player);
        if (destination == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        if (!IntegratedNervMapBuilder.isInstalled(destination))
        {
            source.sendFailure(Component.literal(
                    "The connected map is not installed. Run /seele geofront setup first."));
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        prepareSurfaceLanding(destination);
        player.stopRiding();
        player.teleportTo(destination,
                TOKYO3_ORIGIN.getX() + 0.5D,
                TOKYO3_ORIGIN.getY() + ThirdTokyoSurfaceBuilder.OBSERVATION_Y + 1.0D,
                TOKYO3_ORIGIN.getZ() + ThirdTokyoSurfaceBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 18.0F);
        source.sendSuccess(() -> Component.literal(
                "Tokyo-3 skyline deck. Normal EVA sorties reach this surface through "
                        + "the physical shaft; this command is only a developer camera shortcut."), false);
        return 1;
    }

    private static int exit(CommandSourceStack source) throws CommandSyntaxException
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
        source.sendSuccess(() -> Component.literal(
                "Exited the combined Tokyo-3 / GeoFront development world."), false);
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
        IntegratedAudit result = IntegratedNervMapBuilder.inspect(level);
        logIntegratedAudit("command", result);
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
        if (!IntegratedNervMapBuilder.isInstalled(level))
        {
            source.sendFailure(Component.literal(
                    "The connected map is not installed. Run /seele geofront setup first."));
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        teleportOverview(player, level);
        return 1;
    }

    private static int operations(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        if (!IntegratedNervMapBuilder.isInstalled(level))
        {
            source.sendFailure(Component.literal(
                    "The connected map is not installed. Run /seele geofront setup first."));
            return 0;
        }
        NervOperationsCentreBuilder.OperationsAudit result =
                NervOperationsCentreBuilder.repairRuntimeAccess(level, ORIGIN);
        if (!result.runtimePhysicalValid())
        {
            source.sendFailure(Component.literal(
                    "NERV operations centre failed its structural audit: "
                            + result.summary()));
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        prepareOperationsLanding(level);
        player.stopRiding();
        player.teleportTo(level, ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + 8.0D,
                ORIGIN.getZ() + 18.5D, 180.0F, 0.0F);
        source.sendSuccess(() -> Component.literal(
                "NERV operations centre: tactical command level."), false);
        return 1;
    }

    private static int dogma(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = geoFront(player);
        if (level == null)
        {
            source.sendFailure(Component.literal("GeoFront dimension is unavailable."));
            return 0;
        }
        GeoFrontAudit result = GeoFrontBuilder.inspect(level, ORIGIN);
        if (!result.terminalDogma().valid())
        {
            source.sendFailure(Component.literal(
                    "Terminal Dogma failed its physical-route audit: "
                            + result.terminalDogma().summary()));
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        player.stopRiding();
        player.teleportTo(level, ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + TerminalDogmaBuilder.FACILITY_Y_OFFSET
                        + TerminalDogmaBuilder.OBSERVATION_Y + 1.0D,
                ORIGIN.getZ() + TerminalDogmaBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 0.0F);
        source.sendSuccess(() -> Component.literal(
                "Terminal Dogma observation gallery. This is a developer camera shortcut; "
                        + "the real route begins at the east end of the NERV lower concourse "
                        + "and descends the physical Central Dogma ladder shaft."), false);
        return 1;
    }

    public static ServerLevel geoFront(ServerPlayer player)
    {
        return player.getServer().getLevel(GEOFRONT);
    }

    private static void teleportOverview(ServerPlayer player, ServerLevel level)
    {
        prepareOverviewLanding(level);
        player.stopRiding();
        player.teleportTo(level,
                ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + GeoFrontBuilder.OBSERVATION_Y + 1.0D,
                ORIGIN.getZ() + GeoFrontBuilder.OBSERVATION_Z + 0.5D,
                180.0F, 16.0F);
    }

    private static void prepareOverviewLanding(ServerLevel level)
    {
        BlockPos floor = ORIGIN.offset(0, GeoFrontBuilder.OBSERVATION_Y,
                GeoFrontBuilder.OBSERVATION_Z);
        prepareSafeLanding(level, floor, 4,
                Blocks.SMOOTH_STONE.defaultBlockState(), true);
        setIfDifferent(level, floor, Blocks.LODESTONE.defaultBlockState());
    }

    private static boolean unsafeOverviewLogin(ServerPlayer player,
                                               ServerLevel level)
    {
        if (!level.dimension().equals(GEOFRONT))
        {
            return false;
        }
        BlockPos expectedFloor = ORIGIN.offset(0,
                GeoFrontBuilder.OBSERVATION_Y,
                GeoFrontBuilder.OBSERVATION_Z);
        if (Math.abs(player.getX() - (expectedFloor.getX() + 0.5D)) > 12.0D
                || Math.abs(player.getZ() - (expectedFloor.getZ() + 0.5D)) > 12.0D
                || Math.abs(player.getY() - (expectedFloor.getY() + 1.0D)) > 12.0D)
        {
            return false;
        }
        BlockPos feet = player.blockPosition();
        BlockPos floor = feet.below();
        BlockState floorState = level.getBlockState(floor);
        return !level.getFluidState(feet).isEmpty()
                || floorState.isAir()
                || !floorState.getFluidState().isEmpty()
                || floorState.getCollisionShape(level, floor).isEmpty();
    }

    private static void prepareSurfaceLanding(ServerLevel level)
    {
        BlockPos floor = TOKYO3_ORIGIN.offset(0,
                ThirdTokyoSurfaceBuilder.OBSERVATION_Y,
                ThirdTokyoSurfaceBuilder.OBSERVATION_Z);
        prepareSafeLanding(level, floor, 2,
                Blocks.SMOOTH_STONE.defaultBlockState(), true);
        setIfDifferent(level, floor, Blocks.LODESTONE.defaultBlockState());
    }

    private static void prepareOperationsLanding(ServerLevel level)
    {
        BlockPos floor = ORIGIN.offset(0,
                NervOperationsCentreBuilder.OPERATIONS_FLOOR_Y,
                NervOperationsCentreBuilder.OPERATIONS_ENTRY_Z);
        prepareSafeLanding(level, floor, 1,
                Blocks.POLISHED_BLACKSTONE.defaultBlockState(), false);
    }

    private static void prepareSafeLanding(ServerLevel level, BlockPos floor,
                                           int halfWidth,
                                           BlockState replacementFloor,
                                           boolean replaceDeck)
    {
        for (int x = -halfWidth; x <= halfWidth; x++)
        {
            for (int z = -halfWidth; z <= halfWidth; z++)
            {
                BlockPos deck = floor.offset(x, 0, z);
                level.getChunkAt(deck);
                BlockState current = level.getBlockState(deck);
                if (replaceDeck || current.isAir()
                        || !current.getFluidState().isEmpty()
                        || current.getCollisionShape(level, deck).isEmpty())
                {
                    setIfDifferent(level, deck, replacementFloor);
                }
                for (int y = 1; y <= 4; y++)
                {
                    setIfDifferent(level, deck.above(y),
                            Blocks.AIR.defaultBlockState());
                }
            }
        }
    }

    private static void setIfDifferent(ServerLevel level, BlockPos position,
                                       BlockState state)
    {
        if (!level.getBlockState(position).equals(state))
        {
            level.setBlock(position, state, Block.UPDATE_CLIENTS);
        }
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

    private static void logIntegratedAudit(String stage, IntegratedAudit result)
    {
        if (result.valid())
        {
            ProjectSeele.LOGGER.info("Integrated NERV map audit [{}]: {}",
                    stage, result.summary());
        }
        else
        {
            ProjectSeele.LOGGER.error("INTEGRATED NERV MAP INVALID [{}]: {}",
                    stage, result.summary());
        }
    }
}
