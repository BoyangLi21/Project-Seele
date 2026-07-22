package com.projectseele.event;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.SachielEntity;
import com.projectseele.entity.ShamshelEntity;
import com.projectseele.entity.SiegeAnchorAware;
import com.projectseele.entity.ZeruelEntity;
import com.projectseele.registry.ModEntities;
import com.projectseele.registry.ModItems;
import com.projectseele.world.AngelSiegeSavedData;
import com.projectseele.world.AngelSiegeSavedData.StoredSiege;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraftforge.common.world.ForgeChunkManager;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Persistent three-wave defense event anchored to a player-built NERV beacon. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class AngelSiegeDirector
{
    private static final int[] WAVE_TICKS = {100, 600, 1100};
    private static final int BEACON_MAX_INTEGRITY = 1200;
    private static final int STRUCTURE_ATTACK_INTERVAL = 20;
    private static final double STRUCTURE_ATTACK_RANGE_SQR = 22.0D * 22.0D;
    private static final double EVENT_RANGE = 320.0D;
    private static final Set<UUID> TICKETED = new HashSet<>();

    private AngelSiegeDirector() {}

    public static boolean start(ServerLevel level, BlockPos beacon, ServerPlayer owner)
    {
        if (hasActiveNear(level, beacon))
        {
            return false;
        }
        StoredSiege siege = new StoredSiege(beacon, UUID.randomUUID(),
                owner.getUUID(), level.getGameTime(), 0,
                BEACON_MAX_INTEGRITY, List.of());
        AngelSiegeSavedData.get(level).put(siege);
        acquireTickets(level, siege);
        broadcast(level, beacon, "message.projectseele.siege_started");
        ProjectSeele.LOGGER.info(
                "NERV beacon defense started: event={} beacon={} owner={} integrity={}",
                siege.eventId(), beacon.toShortString(), owner.getStringUUID(),
                BEACON_MAX_INTEGRITY);
        return true;
    }

    public static boolean hasActiveNear(ServerLevel level, BlockPos pos)
    {
        return AngelSiegeSavedData.get(level).nearest(pos, 256.0D).isPresent();
    }

    public static SiegeStatus status(ServerLevel level, BlockPos position)
    {
        StoredSiege siege = AngelSiegeSavedData.get(level)
                .nearest(position, EVENT_RANGE).orElse(null);
        if (siege == null)
        {
            return new SiegeStatus(false, 0, BEACON_MAX_INTEGRITY,
                    BEACON_MAX_INTEGRITY, 0, 0L);
        }
        int alive = 0;
        for (UUID id : siege.spawned())
        {
            if (isAlive(level, id))
            {
                alive++;
            }
        }
        long elapsed = Math.max(0L,
                level.getGameTime() - siege.startedAt());
        return new SiegeStatus(true, siege.nextWave(), siege.integrity(),
                BEACON_MAX_INTEGRITY, alive, elapsed);
    }

    public static OperationResult abort(ServerLevel level, BlockPos position)
    {
        AngelSiegeSavedData data = AngelSiegeSavedData.get(level);
        StoredSiege siege = data.nearest(position, EVENT_RANGE).orElse(null);
        if (siege == null)
        {
            return new OperationResult(false,
                    "No active NERV beacon defense within 320 blocks.");
        }
        for (UUID id : siege.spawned())
        {
            Entity entity = level.getEntity(id);
            if (entity != null)
            {
                entity.discard();
            }
        }
        data.remove(siege.beacon());
        releaseTickets(level, siege);
        broadcast(level, siege.beacon(), "message.projectseele.siege_aborted");
        ProjectSeele.LOGGER.info(
                "NERV beacon defense aborted: event={} beacon={}",
                siege.eventId(), siege.beacon().toShortString());
        return new OperationResult(true,
                "NERV beacon defense aborted; tracked Angels and route tickets cleared.");
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        for (ServerLevel level : event.getServer().getAllLevels())
        {
            tickLevel(level);
        }
    }

    @SubscribeEvent
    public static void onLevelUnload(LevelEvent.Unload event)
    {
        if (!(event.getLevel() instanceof ServerLevel level))
        {
            return;
        }
        for (StoredSiege siege : AngelSiegeSavedData.get(level).sieges())
        {
            releaseTickets(level, siege);
        }
    }

    private static void tickLevel(ServerLevel level)
    {
        AngelSiegeSavedData data = AngelSiegeSavedData.get(level);
        for (StoredSiege initial : data.sieges())
        {
            acquireTickets(level, initial);
            if (!level.getBlockState(initial.beacon()).is(Blocks.LODESTONE))
            {
                fail(level, data, initial, false);
                continue;
            }

            StoredSiege siege = initial;
            long elapsed = Math.max(0L, level.getGameTime() - siege.startedAt());
            while (siege.nextWave() < WAVE_TICKS.length
                    && elapsed >= WAVE_TICKS[siege.nextWave()])
            {
                StoredSiege advanced = spawnWave(level, siege, siege.nextWave());
                if (advanced.nextWave() == siege.nextWave())
                {
                    break;
                }
                siege = advanced;
                data.put(siege);
            }

            guideTrackedAngels(level, siege);
            if (level.getGameTime() % STRUCTURE_ATTACK_INTERVAL == 0L)
            {
                int damage = structureDamage(level, siege);
                if (damage > 0)
                {
                    siege = siege.withIntegrity(siege.integrity() - damage);
                    data.put(siege);
                    if (siege.integrity() <= 0)
                    {
                        fail(level, data, siege, true);
                        continue;
                    }
                }
            }

            if (siege.nextWave() == WAVE_TICKS.length
                    && elapsed > WAVE_TICKS[WAVE_TICKS.length - 1] + 40L
                    && eventChunksLoaded(level, siege)
                    && siege.spawned().stream().noneMatch(id -> isAlive(level, id)))
            {
                complete(level, data, siege);
            }
        }
    }

    private static StoredSiege spawnWave(ServerLevel level, StoredSiege siege, int wave)
    {
        BlockPos spawn = waveSpawn(level, siege.beacon(), wave);
        LivingEntity angel = switch (wave)
        {
            case 0 -> ModEntities.SACHIEL.get().create(level);
            case 1 -> ModEntities.SHAMSHEL.get().create(level);
            default -> ModEntities.ZERUEL.get().create(level);
        };
        if (angel == null)
        {
            ProjectSeele.LOGGER.error(
                    "NERV beacon defense wave {} failed: entity creation returned null",
                    wave + 1);
            return siege;
        }
        angel.moveTo(spawn.getX() + 0.5D, spawn.getY(),
                spawn.getZ() + 0.5D, headingTo(spawn, siege.beacon()), 0.0F);
        if (angel instanceof Mob mob)
        {
            mob.finalizeSpawn(level, level.getCurrentDifficultyAt(spawn),
                    MobSpawnType.EVENT, null, null);
            mob.setPersistenceRequired();
        }
        if (angel instanceof SiegeAnchorAware anchored)
        {
            anchored.setSiegeBeacon(siege.beacon());
        }
        angel.addTag("projectseele.nerv_beacon_siege");
        if (!level.addFreshEntity(angel))
        {
            ProjectSeele.LOGGER.error(
                    "NERV beacon defense wave {} failed: server rejected entity",
                    wave + 1);
            return siege;
        }

        List<UUID> spawned = new ArrayList<>(siege.spawned());
        spawned.add(angel.getUUID());
        StoredSiege advanced = siege.withWave(wave + 1, spawned);
        broadcast(level, siege.beacon(), switch (wave)
        {
            case 0 -> "message.projectseele.siege_wave_sachiel";
            case 1 -> "message.projectseele.siege_wave_shamshel";
            default -> "message.projectseele.siege_wave_zeruel";
        });
        ProjectSeele.LOGGER.info(
                "NERV beacon defense wave {} spawned: event={} entity={} at={}",
                wave + 1, siege.eventId(), angel.getStringUUID(),
                spawn.toShortString());
        return advanced;
    }

    private static void guideTrackedAngels(ServerLevel level, StoredSiege siege)
    {
        for (UUID id : siege.spawned())
        {
            Entity entity = level.getEntity(id);
            if (!(entity instanceof Mob mob) || !mob.isAlive())
            {
                continue;
            }
            if (mob instanceof SiegeAnchorAware anchored)
            {
                anchored.setSiegeBeacon(siege.beacon());
            }
            LivingEntity target = mob.getTarget();
            if (target == null || !target.isAlive())
            {
                mob.getNavigation().moveTo(
                        siege.beacon().getX() + 0.5D,
                        siege.beacon().getY(),
                        siege.beacon().getZ() + 0.5D, 1.0D);
            }
        }
    }

    private static int structureDamage(ServerLevel level, StoredSiege siege)
    {
        int damage = 0;
        for (UUID id : siege.spawned())
        {
            Entity entity = level.getEntity(id);
            if (!(entity instanceof LivingEntity living) || !living.isAlive()
                    || living.distanceToSqr(
                            siege.beacon().getX() + 0.5D,
                            siege.beacon().getY() + 0.5D,
                            siege.beacon().getZ() + 0.5D)
                            > STRUCTURE_ATTACK_RANGE_SQR)
            {
                continue;
            }
            if (living instanceof ZeruelEntity)
            {
                damage += 75;
            }
            else if (living instanceof SachielEntity)
            {
                damage += 45;
            }
            else if (living instanceof ShamshelEntity)
            {
                damage += 30;
            }
        }
        return damage;
    }

    private static boolean isAlive(ServerLevel level, UUID id)
    {
        Entity entity = level.getEntity(id);
        return entity instanceof LivingEntity living && living.isAlive();
    }

    private static void complete(ServerLevel level, AngelSiegeSavedData data,
                                 StoredSiege siege)
    {
        data.remove(siege.beacon());
        releaseTickets(level, siege);
        broadcast(level, siege.beacon(), "message.projectseele.siege_complete");
        ItemStack reward = new ItemStack(ModItems.S2_ENGINE_FRAGMENT.get(), 3);
        ServerPlayer owner = level.getServer().getPlayerList().getPlayer(siege.owner());
        if (owner != null)
        {
            owner.getInventory().placeItemBackInInventory(reward);
        }
        else
        {
            level.addFreshEntity(new ItemEntity(level,
                    siege.beacon().getX() + 0.5D,
                    siege.beacon().getY() + 1.25D,
                    siege.beacon().getZ() + 0.5D, reward));
        }
        ProjectSeele.LOGGER.info(
                "NERV beacon defense complete: event={} beacon={} owner={} reward=3",
                siege.eventId(), siege.beacon().toShortString(), siege.owner());
    }

    private static void fail(ServerLevel level, AngelSiegeSavedData data,
                             StoredSiege siege, boolean destroyBeacon)
    {
        if (destroyBeacon)
        {
            level.destroyBlock(siege.beacon().above(), false);
            level.destroyBlock(siege.beacon(), false);
        }
        data.remove(siege.beacon());
        releaseTickets(level, siege);
        broadcast(level, siege.beacon(), "message.projectseele.siege_failed");
        ProjectSeele.LOGGER.info(
                "NERV beacon defense failed: event={} beacon={} integrity={}",
                siege.eventId(), siege.beacon().toShortString(), siege.integrity());
    }

    private static void acquireTickets(ServerLevel level, StoredSiege siege)
    {
        if (!TICKETED.add(siege.eventId()))
        {
            return;
        }
        for (ChunkPos chunk : eventChunks(siege.beacon()))
        {
            ForgeChunkManager.forceChunk(level, ProjectSeele.MODID,
                    siege.eventId(), chunk.x, chunk.z, true, true);
        }
    }

    private static void releaseTickets(ServerLevel level, StoredSiege siege)
    {
        for (ChunkPos chunk : eventChunks(siege.beacon()))
        {
            ForgeChunkManager.forceChunk(level, ProjectSeele.MODID,
                    siege.eventId(), chunk.x, chunk.z, false, true);
        }
        TICKETED.remove(siege.eventId());
    }

    private static boolean eventChunksLoaded(ServerLevel level, StoredSiege siege)
    {
        for (ChunkPos chunk : eventChunks(siege.beacon()))
        {
            if (!level.hasChunk(chunk.x, chunk.z))
            {
                return false;
            }
        }
        return true;
    }

    private static Set<ChunkPos> eventChunks(BlockPos beacon)
    {
        Set<ChunkPos> chunks = new HashSet<>();
        chunks.add(new ChunkPos(beacon));
        for (int wave = 0; wave < WAVE_TICKS.length; wave++)
        {
            double angle = wave * Math.PI * 2.0D / WAVE_TICKS.length;
            for (int step = 1; step <= 7; step++)
            {
                double distance = 92.0D * step / 7.0D;
                int x = beacon.getX() + (int) Math.round(Math.cos(angle) * distance);
                int z = beacon.getZ() + (int) Math.round(Math.sin(angle) * distance);
                chunks.add(new ChunkPos(new BlockPos(x, beacon.getY(), z)));
            }
        }
        return chunks;
    }

    private static BlockPos waveSpawn(ServerLevel level, BlockPos beacon, int wave)
    {
        double angle = wave * Math.PI * 2.0D / WAVE_TICKS.length;
        int x = beacon.getX() + (int) Math.round(Math.cos(angle) * 92.0D);
        int z = beacon.getZ() + (int) Math.round(Math.sin(angle) * 92.0D);
        int y = level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z) + 1;
        if (wave == 1)
        {
            y += 14;
        }
        return new BlockPos(x, y, z);
    }

    private static float headingTo(BlockPos from, BlockPos target)
    {
        return (float) Math.toDegrees(Math.atan2(
                target.getZ() - from.getZ(), target.getX() - from.getX())) - 90.0F;
    }

    private static void broadcast(ServerLevel level, BlockPos center, String key)
    {
        for (ServerPlayer player : level.players())
        {
            if (player.blockPosition().closerThan(center, EVENT_RANGE))
            {
                player.displayClientMessage(Component.translatable(key), false);
            }
        }
    }

    public record OperationResult(boolean accepted, String message) {}

    public record SiegeStatus(boolean active, int wave, int integrity,
                              int maximumIntegrity, int aliveAngels,
                              long elapsedTicks)
    {
        public String summary()
        {
            if (!this.active)
            {
                return "NERV beacon defense: STANDBY";
            }
            return String.format(java.util.Locale.ROOT,
                    "NERV beacon defense: wave=%d/3 integrity=%d/%d "
                            + "hostiles=%d elapsed=%ds",
                    this.wave, this.integrity, this.maximumIntegrity,
                    this.aliveAngels, this.elapsedTicks / 20L);
        }
    }
}