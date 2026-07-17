package com.projectseele.visual;

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
import com.projectseele.world.GeoFrontBuilder.GeoFrontAudit;
import com.projectseele.world.IntegratedNervMapBuilder;
import com.projectseele.world.IntegratedNervMapBuilder.IntegratedAudit;
import com.projectseele.world.IntegratedNervMapBuilder.LiftLink;
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
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.RegisterCommandsEvent;
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
                        .then(Commands.literal("overview")
                                .executes(context -> overview(context.getSource())))));
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
                "Connected Tokyo-3 / GeoFront map ready: three physical 286-block shafts. "
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
        level.setDayTime(6000L);
        level.setWeatherParameters(12000, 0, false, false);
        IntegratedAudit result = IntegratedNervMapBuilder.ensure(level);
        logIntegratedAudit("visual-setup", result);
        if (!result.valid())
        {
            throw new IllegalStateException(
                    "Integrated GeoFront visual setup failed audit: " + result.summary());
        }
        BlockPos hiddenPlatform = ORIGIN.offset(0, 3, 0);
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
        IntegratedAudit result = IntegratedNervMapBuilder.inspect(level);
        if (!result.valid())
        {
            source.sendFailure(Component.literal(
                    "The continuous map has not passed setup. "
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
        IntegratedAudit mapAudit = IntegratedNervMapBuilder.ensure(geoFront);
        Tokyo3RetractionDirector.register(geoFront, TOKYO3_ORIGIN);
        if (!mapAudit.valid())
        {
            source.sendFailure(Component.literal(
                    "Connected map failed its audit: " + mapAudit.summary()));
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
                "Physical sortie ready: Unit-00/01/02 are frozen at the lower stations. "
                        + "Launch travels the same 286-block shaft into Tokyo-3; no portal or EVA teleport."), false);
        return 1;
    }

    private static List<EvaUnit01Entity> ensureContinuousSortieUnits(ServerLevel level)
    {
        int lowerY = IntegratedNervMapBuilder.lowerLiftBed(1).getY();
        int surfaceY = IntegratedNervMapBuilder.surfaceLiftBed(1).getY();
        AABB mapArea = new AABB(-256.0D, lowerY - 32.0D, -256.0D,
                256.0D, surfaceY + 72.0D, 256.0D);
        List<EvaUnit01Entity> all = new java.util.ArrayList<>(
                level.getEntitiesOfClass(
                        EvaUnit01Entity.class, mapArea, EvaUnit01Entity::isAlive));
        List<EvaUnit01Entity> linked = new java.util.ArrayList<>(3);
        for (LiftLink lift : IntegratedNervMapBuilder.liftLinks())
        {
            int variant = lift.index();
            List<EvaUnit01Entity> lowerUnits = all.stream()
                    .filter(unit -> unit.getUnitVariant() == variant)
                    .filter(unit -> unit.distanceToSqr(
                            lift.lowerBed().getX() + 0.5D,
                            lift.lowerBed().getY() + 1.0D,
                            lift.lowerBed().getZ() + 0.5D) < 196.0D)
                    .toList();
            if (lowerUnits.size() > 1)
            {
                throw new IllegalStateException(
                        "Lower station contains duplicate Unit-0" + variant + " entities.");
            }
            EvaUnit01Entity unit = lowerUnits.isEmpty() ? null : lowerUnits.get(0);
            if (unit == null)
            {
                EvaUnit01Entity existing = all.stream()
                        .filter(candidate -> candidate.getUnitVariant() == variant)
                        .findFirst().orElse(null);
                if (existing != null)
                {
                    throw new IllegalStateException(
                            "Unit-0" + variant + " already exists in the connected map at "
                                    + existing.blockPosition().toShortString() + ".");
                }
                unit = createUnit(level, variant);
                if (unit == null)
                {
                    throw new IllegalStateException(
                            "Failed to create Unit-0" + variant + " for its lower station.");
                }
                unit.moveTo(lift.lowerBed().getX() + 0.5D,
                        lift.lowerBed().getY() + 1.0D,
                        lift.lowerBed().getZ() + 0.5D,
                        EvaUnit01Entity.SILO_BAY_YAW, 0.0F);
                unit.setPersistenceRequired();
                if (!level.addFreshEntity(unit))
                {
                    throw new IllegalStateException(
                            "Server rejected Unit-0" + variant + " deployment.");
                }
                all.add(unit);
            }
            if (unit.isVehicle() || unit.isPassenger() || unit.isLaunchSequenceActive())
            {
                throw new IllegalStateException(
                        "Unit-0" + variant + " is occupied or already launching.");
            }
            unit.moveTo(lift.lowerBed().getX() + 0.5D,
                    lift.lowerBed().getY() + 1.0D,
                    lift.lowerBed().getZ() + 0.5D,
                    EvaUnit01Entity.SILO_BAY_YAW, 0.0F);
            unit.setYRot(EvaUnit01Entity.SILO_BAY_YAW);
            unit.setYBodyRot(EvaUnit01Entity.SILO_BAY_YAW);
            unit.setYHeadRot(EvaUnit01Entity.SILO_BAY_YAW);
            unit.yRotO = EvaUnit01Entity.SILO_BAY_YAW;
            unit.yBodyRotO = EvaUnit01Entity.SILO_BAY_YAW;
            unit.yHeadRotO = EvaUnit01Entity.SILO_BAY_YAW;
            unit.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
            unit.setNoGravity(true);
            unit.setSortieDestination(level.dimension(), lift.surfaceBed());
            unit.setSortieParkingBed(lift.lowerBed());
            linked.add(unit);
        }
        return linked;
    }

    private static EvaUnit01Entity createUnit(ServerLevel level, int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> ModEntities.EVA_UNIT00.get().create(level);
            case EvaUnit01Entity.UNIT_02 -> ModEntities.EVA_UNIT02.get().create(level);
            default -> ModEntities.EVA_UNIT01.get().create(level);
        };
    }

    /** Dedicated-world reset before the unattended cross-dimension sortie. */
    static void preloadVisualSortie(ServerPlayer player)
    {
        ServerLevel geoFront = geoFront(player);
        if (geoFront == null)
        {
            throw new IllegalStateException("GeoFront visual sortie dimension is unavailable");
        }
        IntegratedAudit audit = IntegratedNervMapBuilder.ensure(geoFront);
        if (!audit.valid())
        {
            throw new IllegalStateException(
                    "GeoFront visual sortie preload failed: " + audit.summary());
        }
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
                        384.0D, GeoFrontBuilder.CAVERN_RADIUS + 32.0D));
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
                        384.0D, GeoFrontBuilder.CAVERN_RADIUS + 32.0D));
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
        IntegratedAudit audit = IntegratedNervMapBuilder.inspect(destination);
        if (!audit.valid())
        {
            source.sendFailure(Component.literal(
                    "Connected map is incomplete. Run /seele geofront setup first."));
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
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
        GeoFrontAudit result = GeoFrontBuilder.inspect(level, ORIGIN);
        if (!result.operations().valid())
        {
            source.sendFailure(Component.literal(
                    "NERV operations centre failed its structural audit: "
                            + result.operations().summary()));
            return 0;
        }
        if (!player.serverLevel().dimension().equals(GEOFRONT))
        {
            saveReturn(player);
        }
        player.stopRiding();
        player.teleportTo(level, ORIGIN.getX() + 0.5D,
                ORIGIN.getY() + 8.0D,
                ORIGIN.getZ() + 18.5D, 180.0F, 0.0F);
        source.sendSuccess(() -> Component.literal(
                "NERV operations centre: tactical command level."), false);
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
