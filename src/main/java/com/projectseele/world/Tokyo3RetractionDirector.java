package com.projectseele.world;

import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModBlocks;
import com.projectseele.world.Tokyo3RetractionSavedData.StoredDistrict;
import net.minecraft.core.BlockPos;
import net.minecraft.core.SectionPos;
import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Tick-budgeted, persistent travel of every generated Tokyo-3 high-rise. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class Tokyo3RetractionDirector
{
    public static final int TICKS_PER_LAYER = 20;
    /**
     * Towers of one layer are stepped across this many ticks. The client
     * retraction audit needs a settled skyline for twelve consecutive ticks
     * inside every layer period, so this has to stay a small fraction of
     * {@link #TICKS_PER_LAYER}.
     */
    private static final int LAYER_SPREAD_TICKS = 5;
    /**
     * Self-expiring, non-persistent load ticket. The order is given from the
     * GeoFront command centre some five hundred blocks below the skyline,
     * where none of the district is resident: without a ticket the travel
     * either never starts or makes every placement block on a chunk load.
     */
    private static final TicketType<ChunkPos> TRAVEL_TICKET = TicketType.create(
            "projectseele_tokyo3_travel", Comparator.comparingLong(ChunkPos::toLong),
            TICKS_PER_LAYER * 3);
    private static final int TICKET_CLAIMS_PER_TICK = 12;
    private static final Map<Long, long[]> TRAVEL_CHUNKS = new ConcurrentHashMap<>();
    /** How much of {@link #travelChunks} each district has claimed so far. */
    private static final Map<Long, Integer> TICKET_CURSOR = new ConcurrentHashMap<>();
    /** Block-work cost of the travel in progress, per district origin. */
    private static final Map<Long, TravelCost> TRAVEL_COST = new ConcurrentHashMap<>();
    private static final double CORE_CONTROL_RANGE = 150.0D;

    private Tokyo3RetractionDirector() {}

    public static void register(ServerLevel level, BlockPos origin)
    {
        StoredDistrict district = ensure(level, origin);
        updateCoreStates(level, origin,
                district.depth() > 0 || district.targetDepth() > 0);
    }

    /** Deterministic reset reserved for isolated unattended visual fixtures. */
    public static void reset(ServerLevel level, BlockPos origin)
    {
        Tokyo3RetractionSavedData.get(level).put(new StoredDistrict(
                origin, 0, 0, level.getGameTime()));
        updateCoreStates(level, origin, false);
    }

    public static int depth(ServerLevel level, BlockPos origin)
    {
        return ensure(level, origin).depth();
    }

    public static RequestResult request(ServerLevel level, BlockPos origin,
                                        boolean retract)
    {
        StoredDistrict current = settleLayer(level, ensure(level, origin));
        int target = retract ? ThirdTokyoSurfaceBuilder.maximumRetractionDepth() : 0;
        if (current.depth() == target && current.targetDepth() == target)
        {
            return new RequestResult(false, retract
                    ? "Tokyo-3 armour towers are already fully retracted."
                    : "Tokyo-3 armour towers are already at street level.");
        }
        if (current.targetDepth() == target && current.depth() != target)
        {
            return new RequestResult(false, retract
                    ? "Tokyo-3 armour towers are already descending."
                    : "Tokyo-3 armour towers are already rising.");
        }

        Tokyo3RetractionSavedData.get(level).put(new StoredDistrict(
                origin, current.depth(), target, level.getGameTime() + TICKS_PER_LAYER));
        updateCoreStates(level, origin, retract);
        level.playSound(null, origin, retract ? SoundEvents.PISTON_CONTRACT
                : SoundEvents.PISTON_EXTEND, SoundSource.BLOCKS, 4.0F, 0.55F);
        ProjectSeele.LOGGER.info("Tokyo-3 armour towers {} requested at {} depth={}/{}",
                retract ? "retraction" : "restoration", origin.toShortString(),
                current.depth(), target);
        return new RequestResult(true, retract
                ? "Tokyo-3 emergency configuration: armour towers descending."
                : "Tokyo-3 all-clear configuration: armour towers rising.");
    }

    public static RequestResult toggleNearest(ServerLevel level, BlockPos position)
    {
        return Tokyo3RetractionSavedData.get(level)
                .nearest(position, CORE_CONTROL_RANGE)
                .map(district -> request(level, district.origin(),
                        district.targetDepth() == 0))
                .orElseGet(() -> new RequestResult(false,
                        "No registered Tokyo-3 district is linked to this core."));
    }

    public static Status status(ServerLevel level, BlockPos origin)
    {
        StoredDistrict district = ensure(level, origin);
        String phase;
        if (district.depth() == district.targetDepth())
        {
            phase = district.depth() == 0 ? "DEPLOYED" : "RETRACTED";
        }
        else
        {
            phase = district.targetDepth() > district.depth()
                    ? "DESCENDING" : "RISING";
        }
        return new Status(phase, district.depth(), district.targetDepth(),
                ThirdTokyoSurfaceBuilder.maximumRetractionDepth());
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        MinecraftServer server = event.getServer();
        for (ServerLevel level : server.getAllLevels())
        {
            tickLevel(level);
        }
    }

    private static void tickLevel(ServerLevel level)
    {
        Tokyo3RetractionSavedData data = Tokyo3RetractionSavedData.get(level);
        long gameTime = level.getGameTime();
        for (StoredDistrict district : data.districts())
        {
            if (district.depth() == district.targetDepth())
            {
                continue;
            }
            boolean layerInFlight = district.cursor() > 0;
            if (!layerInFlight && gameTime < district.nextStepAt())
            {
                continue;
            }
            if (!layerInFlight)
            {
                // Outlives one layer period, so a layer already under way is
                // still covered without re-issuing every tick.
                acquireTravelTickets(level, district.origin());
            }
            if (!districtLoaded(level, district.origin()))
            {
                // The tickets were only just issued; retry once they resolve.
                continue;
            }

            int direction = Integer.signum(district.targetDepth() - district.depth());
            int nextDepth = district.depth() + direction;
            if (!layerInFlight && direction < 0 && restorationOccupied(
                    level, district.origin(), district.depth(), nextDepth))
            {
                data.put(new StoredDistrict(district.origin(), district.depth(),
                        district.targetDepth(), gameTime + TICKS_PER_LAYER));
                continue;
            }

            int towers = ThirdTokyoSurfaceBuilder.movableBuildings().size();
            int budget = Math.max(1,
                    (towers + LAYER_SPREAD_TICKS - 1) / LAYER_SPREAD_TICKS);
            int reached = Math.min(towers, district.cursor() + budget);
            long started = System.nanoTime();
            for (int index = district.cursor(); index < reached; index++)
            {
                ThirdTokyoSurfaceBuilder.applyRetractionDepth(level, district.origin(),
                        district.depth(), nextDepth, index);
            }
            TRAVEL_COST.computeIfAbsent(district.origin().asLong(), key -> new TravelCost())
                    .layerNanos += System.nanoTime() - started;
            // The period is measured from the layer's first tower, so spreading
            // the writes never slows the one-block-per-second cadence.
            long nextStepAt = layerInFlight
                    ? district.nextStepAt() : gameTime + TICKS_PER_LAYER;
            if (reached < towers)
            {
                data.put(new StoredDistrict(district.origin(), district.depth(),
                        district.targetDepth(), nextStepAt, reached));
                continue;
            }

            LocalMapAssetLoader.applyTokyo3RetractionDepth(level,
                    district.origin(), district.depth(), nextDepth);
            emitLayerEffect(level, district.origin(), direction > 0);
            data.put(new StoredDistrict(district.origin(), nextDepth,
                    district.targetDepth(), nextStepAt));
            TravelCost cost = TRAVEL_COST.get(district.origin().asLong());
            cost.closeLayer();
            if (nextDepth == district.targetDepth())
            {
                boolean retracted = nextDepth > 0;
                updateCoreStates(level, district.origin(), retracted);
                releaseTravelTickets(level, district.origin());
                level.playSound(null, district.origin(), SoundEvents.IRON_DOOR_CLOSE,
                        SoundSource.BLOCKS, 5.0F, retracted ? 0.55F : 0.85F);
                TRAVEL_COST.remove(district.origin().asLong());
                // A layer has to stay small against the 50ms tick budget. Peak
                // is the number that matters: it used to be the whole district
                // rewritten inside a single tick.
                ProjectSeele.LOGGER.info(
                        "Tokyo-3 armour towers {} at {} depth={} towers={} "
                                + "layers={} blockWork={}ms peakLayer={}ms",
                        retracted ? "fully retracted" : "fully restored",
                        district.origin().toShortString(), nextDepth, towers,
                        cost.layers, cost.totalNanos / 1_000_000L,
                        cost.peakNanos / 1_000_000L);
            }
        }
    }

    /** Every chunk a tower lot touches, so travel never waits on a chunk load. */
    private static long[] travelChunks(BlockPos origin)
    {
        return TRAVEL_CHUNKS.computeIfAbsent(origin.asLong(), key ->
        {
            Set<Long> chunks = new LinkedHashSet<>();
            for (ThirdTokyoSurfaceBuilder.TowerSpec tower
                    : ThirdTokyoSurfaceBuilder.movableBuildings())
            {
                int half = tower.halfSize();
                int centreX = origin.getX() + tower.x();
                int centreZ = origin.getZ() + tower.z();
                for (int x = SectionPos.blockToSectionCoord(centreX - half);
                     x <= SectionPos.blockToSectionCoord(centreX + half); x++)
                {
                    for (int z = SectionPos.blockToSectionCoord(centreZ - half);
                         z <= SectionPos.blockToSectionCoord(centreZ + half); z++)
                    {
                        chunks.add(ChunkPos.asLong(x, z));
                    }
                }
            }
            return chunks.stream().mapToLong(Long::longValue).toArray();
        });
    }

    /**
     * Claims the travel chunks a slice at a time. A cold district is some three
     * hundred chunks, and claiming them in one tick costs a second of chunk
     * loading up front; {@link #districtLoaded} holds the first layer back
     * until they have all arrived either way, so the ramp is free.
     */
    private static void acquireTravelTickets(ServerLevel level, BlockPos origin)
    {
        long[] chunks = travelChunks(origin);
        int claimed = TICKET_CURSOR.getOrDefault(origin.asLong(), 0);
        int end = claimed >= chunks.length
                ? chunks.length
                : Math.min(chunks.length, claimed + TICKET_CLAIMS_PER_TICK);
        // Re-ticketing a resident chunk is free, and the ticket has to outlive
        // the layer period, so a settled district refreshes the whole set.
        for (int index = claimed >= chunks.length ? 0 : claimed; index < end; index++)
        {
            ChunkPos chunk = new ChunkPos(chunks[index]);
            level.getChunkSource().addRegionTicket(TRAVEL_TICKET, chunk, 0, chunk);
        }
        TICKET_CURSOR.put(origin.asLong(), end);
    }

    private static void releaseTravelTickets(ServerLevel level, BlockPos origin)
    {
        TICKET_CURSOR.remove(origin.asLong());
        for (long packed : travelChunks(origin))
        {
            ChunkPos chunk = new ChunkPos(packed);
            level.getChunkSource().removeRegionTicket(TRAVEL_TICKET, chunk, 0, chunk);
        }
    }

    /**
     * Finishes a part-stepped layer before the operator is allowed to reverse
     * it. Towers left mid-layer would otherwise sit one block out of step with
     * the record and grow a wall ring above their own roof.
     */
    private static StoredDistrict settleLayer(ServerLevel level, StoredDistrict district)
    {
        if (district.cursor() <= 0)
        {
            return district;
        }
        int direction = Integer.signum(district.targetDepth() - district.depth());
        int settledDepth = district.depth() + direction;
        int towers = ThirdTokyoSurfaceBuilder.movableBuildings().size();
        for (int index = district.cursor(); direction != 0 && index < towers; index++)
        {
            ThirdTokyoSurfaceBuilder.applyRetractionDepth(level, district.origin(),
                    district.depth(), settledDepth, index);
        }
        LocalMapAssetLoader.applyTokyo3RetractionDepth(level,
                district.origin(), district.depth(), settledDepth);
        StoredDistrict settled = new StoredDistrict(district.origin(), settledDepth,
                district.targetDepth(), district.nextStepAt());
        Tokyo3RetractionSavedData.get(level).put(settled);
        return settled;
    }

    private static StoredDistrict ensure(ServerLevel level, BlockPos origin)
    {
        Tokyo3RetractionSavedData data = Tokyo3RetractionSavedData.get(level);
        return data.get(origin).orElseGet(() -> {
            StoredDistrict created = new StoredDistrict(origin, 0, 0,
                    level.getGameTime());
            data.put(created);
            return created;
        });
    }

    /**
     * Only the tower lots are written, and only those are ticketed. Gating on
     * the far district corners instead would stall the travel forever whenever
     * the order is given from underground.
     */
    private static boolean districtLoaded(ServerLevel level, BlockPos origin)
    {
        for (long packed : travelChunks(origin))
        {
            ChunkPos chunk = new ChunkPos(packed);
            if (!level.hasChunk(chunk.x, chunk.z))
            {
                return false;
            }
        }
        return true;
    }

    private static boolean restorationOccupied(ServerLevel level, BlockPos origin,
                                                int oldDepth, int newDepth)
    {
        for (ThirdTokyoSurfaceBuilder.TowerSpec tower
                : ThirdTokyoSurfaceBuilder.movableBuildings())
        {
            int oldVisible = Math.max(0, tower.height() - oldDepth);
            int newVisible = Math.max(0, tower.height() - newDepth);
            if (newVisible <= oldVisible)
            {
                continue;
            }
            BlockPos centre = origin.offset(tower.x(), 0, tower.z());
            int half = tower.halfSize();
            AABB layer = new AABB(
                    centre.getX() - half, centre.getY() + newVisible,
                    centre.getZ() - half,
                    centre.getX() + half + 1, centre.getY() + newVisible + 3,
                    centre.getZ() + half + 1);
            if (!level.getEntitiesOfClass(LivingEntity.class, layer,
                    entity -> entity.isAlive() && !entity.isSpectator()
                            && (entity instanceof net.minecraft.world.entity.player.Player
                            || entity instanceof EvaUnit01Entity)).isEmpty())
            {
                return true;
            }
        }
        return false;
    }

    private static void emitLayerEffect(ServerLevel level, BlockPos origin,
                                        boolean retracting)
    {
        BlockParticleOption dust = new BlockParticleOption(ParticleTypes.BLOCK,
                net.minecraft.world.level.block.Blocks.DEEPSLATE_TILES.defaultBlockState());
        int index = 0;
        for (ThirdTokyoSurfaceBuilder.TowerSpec tower
                : ThirdTokyoSurfaceBuilder.movableBuildings())
        {
            if ((index++ & 3) != 0)
            {
                continue;
            }
            BlockPos centre = origin.offset(tower.x(), 1, tower.z());
            level.sendParticles(dust, centre.getX() + 0.5D,
                    centre.getY() + 0.25D, centre.getZ() + 0.5D,
                    6, tower.halfSize() * 0.6D, 0.3D,
                    tower.halfSize() * 0.6D, 0.04D);
        }
        level.playSound(null, origin, retracting ? SoundEvents.PISTON_CONTRACT
                : SoundEvents.PISTON_EXTEND, SoundSource.BLOCKS, 3.2F,
                retracting ? 0.48F : 0.65F);
    }

    private static void updateCoreStates(ServerLevel level, BlockPos origin, boolean armed)
    {
        for (ThirdTokyoSurfaceBuilder.TowerSpec tower
                : ThirdTokyoSurfaceBuilder.armouredTowers())
        {
            BlockPos core = origin.offset(tower.x(), 0, tower.z());
            BlockState state = level.getBlockState(core);
            if (state.is(ModBlocks.RETRACTABLE_BUILDING_CORE.get()))
            {
                level.setBlock(core,
                        state.setValue(RetractableBuildingCoreBlock.ARMED, armed),
                        net.minecraft.world.level.block.Block.UPDATE_CLIENTS);
            }
        }
    }

    private static final class TravelCost
    {
        private long layerNanos;
        private long totalNanos;
        private long peakNanos;
        private int layers;

        private void closeLayer()
        {
            this.totalNanos += this.layerNanos;
            this.peakNanos = Math.max(this.peakNanos, this.layerNanos);
            this.layerNanos = 0L;
            this.layers++;
        }
    }

    public record RequestResult(boolean accepted, String message) {}

    public record Status(String phase, int depth, int targetDepth, int maximumDepth) {}
}
