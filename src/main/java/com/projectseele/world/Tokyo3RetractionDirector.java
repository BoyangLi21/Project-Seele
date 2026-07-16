package com.projectseele.world;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModBlocks;
import com.projectseele.world.Tokyo3RetractionSavedData.StoredDistrict;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.BlockParticleOption;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Tick-budgeted, persistent retraction of the thirteen Tokyo-3 armour towers. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class Tokyo3RetractionDirector
{
    public static final int TICKS_PER_LAYER = 20;
    private static final double CORE_CONTROL_RANGE = 150.0D;

    private Tokyo3RetractionDirector() {}

    public static void register(ServerLevel level, BlockPos origin)
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
        StoredDistrict current = ensure(level, origin);
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
            if (district.depth() == district.targetDepth()
                    || gameTime < district.nextStepAt()
                    || !districtLoaded(level, district.origin()))
            {
                continue;
            }
            int direction = Integer.signum(district.targetDepth() - district.depth());
            int nextDepth = district.depth() + direction;
            if (direction < 0 && restorationOccupied(level, district.origin(),
                    district.depth(), nextDepth))
            {
                data.put(new StoredDistrict(district.origin(), district.depth(),
                        district.targetDepth(), gameTime + TICKS_PER_LAYER));
                continue;
            }

            ThirdTokyoSurfaceBuilder.applyRetractionDepth(level, district.origin(),
                    district.depth(), nextDepth);
            emitLayerEffect(level, district.origin(), direction > 0);
            StoredDistrict updated = new StoredDistrict(district.origin(), nextDepth,
                    district.targetDepth(), gameTime + TICKS_PER_LAYER);
            data.put(updated);
            if (nextDepth == district.targetDepth())
            {
                boolean retracted = nextDepth > 0;
                updateCoreStates(level, district.origin(), retracted);
                level.playSound(null, district.origin(), SoundEvents.IRON_DOOR_CLOSE,
                        SoundSource.BLOCKS, 5.0F, retracted ? 0.55F : 0.85F);
                ProjectSeele.LOGGER.info(
                        "Tokyo-3 armour towers {} at {} depth={}",
                        retracted ? "fully retracted" : "fully restored",
                        district.origin().toShortString(), nextDepth);
            }
        }
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

    private static boolean districtLoaded(ServerLevel level, BlockPos origin)
    {
        int edge = ThirdTokyoSurfaceBuilder.DISTRICT_HALF_SIZE;
        return level.hasChunkAt(origin.offset(-edge, 0, -edge))
                && level.hasChunkAt(origin.offset(edge, 0, -edge))
                && level.hasChunkAt(origin.offset(-edge, 0, edge))
                && level.hasChunkAt(origin.offset(edge, 0, edge));
    }

    private static boolean restorationOccupied(ServerLevel level, BlockPos origin,
                                                int oldDepth, int newDepth)
    {
        for (ThirdTokyoSurfaceBuilder.TowerSpec tower
                : ThirdTokyoSurfaceBuilder.armouredTowers())
        {
            int oldVisible = Math.max(0, tower.height() - oldDepth);
            int newVisible = Math.max(0, tower.height() - newDepth);
            if (newVisible <= oldVisible)
            {
                continue;
            }
            BlockPos centre = origin.offset(tower.x(), 0, tower.z());
            int half = ThirdTokyoSurfaceBuilder.ARMOURED_LOT_HALF_SIZE;
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
        for (ThirdTokyoSurfaceBuilder.TowerSpec tower
                : ThirdTokyoSurfaceBuilder.armouredTowers())
        {
            BlockPos centre = origin.offset(tower.x(), 1, tower.z());
            level.sendParticles(dust, centre.getX() + 0.5D,
                    centre.getY() + 0.25D, centre.getZ() + 0.5D,
                    20, 9.0D, 0.4D, 9.0D, 0.06D);
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

    public record RequestResult(boolean accepted, String message) {}

    public record Status(String phase, int depth, int targetDepth, int maximumDepth) {}
}
