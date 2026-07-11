package com.projectseele.event;

import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.ShamshelEntity;
import com.projectseele.registry.ModEntities;
import com.projectseele.registry.ModItems;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Transient three-wave defense event anchored to a player-built NERV beacon. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class AngelSiegeDirector
{
    private static final List<Siege> ACTIVE = new ArrayList<>();
    private static final int[] WAVE_TICKS = {100, 600, 1100};

    private AngelSiegeDirector() {}

    public static boolean start(ServerLevel level, BlockPos beacon, ServerPlayer owner)
    {
        if (hasActiveNear(level, beacon))
        {
            return false;
        }
        ACTIVE.add(new Siege(level, beacon.immutable(), owner.getUUID()));
        broadcast(level, beacon, "message.projectseele.siege_started");
        return true;
    }

    public static boolean hasActiveNear(ServerLevel level, BlockPos pos)
    {
        return ACTIVE.stream().anyMatch(s -> s.level == level && s.beacon.closerThan(pos, 256.0D));
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END || ACTIVE.isEmpty())
        {
            return;
        }
        Iterator<Siege> iterator = ACTIVE.iterator();
        while (iterator.hasNext())
        {
            Siege siege = iterator.next();
            if (!siege.level.getBlockState(siege.beacon).is(net.minecraft.world.level.block.Blocks.LODESTONE))
            {
                broadcast(siege.level, siege.beacon, "message.projectseele.siege_failed");
                iterator.remove();
                continue;
            }
            siege.ticks++;
            if (siege.nextWave < WAVE_TICKS.length && siege.ticks >= WAVE_TICKS[siege.nextWave])
            {
                spawnWave(siege, siege.nextWave++);
            }
            if (siege.nextWave == WAVE_TICKS.length && siege.ticks > WAVE_TICKS[2] + 40
                    && siege.spawned.stream().noneMatch(id -> isAlive(siege.level, id)))
            {
                complete(siege);
                iterator.remove();
            }
        }
    }

    private static void spawnWave(Siege siege, int wave)
    {
        double angle = wave * Math.PI * 2.0D / 3.0D;
        int x = siege.beacon.getX() + (int) Math.round(Math.cos(angle) * 92.0D);
        int z = siege.beacon.getZ() + (int) Math.round(Math.sin(angle) * 92.0D);
        int y = siege.level.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x, z) + 1;
        LivingEntity angel = switch (wave)
        {
            case 0 -> ModEntities.SACHIEL.get().create(siege.level);
            case 1 -> ModEntities.SHAMSHEL.get().create(siege.level);
            default -> ModEntities.ZERUEL.get().create(siege.level);
        };
        if (angel == null)
        {
            return;
        }
        if (angel instanceof ShamshelEntity)
        {
            y += 14;
        }
        angel.moveTo(x + 0.5D, y, z + 0.5D, (float) Math.toDegrees(-angle), 0.0F);
        if (angel instanceof net.minecraft.world.entity.Mob mob)
        {
            mob.setPersistenceRequired();
        }
        siege.level.addFreshEntity(angel);
        siege.spawned.add(angel.getUUID());
        broadcast(siege.level, siege.beacon, switch (wave)
        {
            case 0 -> "message.projectseele.siege_wave_sachiel";
            case 1 -> "message.projectseele.siege_wave_shamshel";
            default -> "message.projectseele.siege_wave_zeruel";
        });
    }

    private static boolean isAlive(ServerLevel level, UUID id)
    {
        Entity entity = level.getEntity(id);
        return entity instanceof LivingEntity living && living.isAlive();
    }

    private static void complete(Siege siege)
    {
        broadcast(siege.level, siege.beacon, "message.projectseele.siege_complete");
        ServerPlayer owner = siege.level.getServer().getPlayerList().getPlayer(siege.owner);
        if (owner != null)
        {
            owner.getInventory().placeItemBackInInventory(new ItemStack(ModItems.S2_ENGINE_FRAGMENT.get(), 3));
        }
    }

    private static void broadcast(ServerLevel level, BlockPos center, String key)
    {
        for (ServerPlayer player : level.players())
        {
            if (player.blockPosition().closerThan(center, 320.0D))
            {
                player.displayClientMessage(Component.translatable(key), false);
            }
        }
    }

    private static final class Siege
    {
        final ServerLevel level;
        final BlockPos beacon;
        final UUID owner;
        final List<UUID> spawned = new ArrayList<>();
        int ticks;
        int nextWave;

        Siege(ServerLevel level, BlockPos beacon, UUID owner)
        {
            this.level = level;
            this.beacon = beacon;
            this.owner = owner;
        }
    }
}
