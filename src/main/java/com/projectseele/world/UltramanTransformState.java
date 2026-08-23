package com.projectseele.world;

import com.projectseele.network.ClientboundUltramanStatePacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModItems;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraftforge.network.PacketDistributor;

/** Server-authoritative Hayata-to-Ultraman transformation state. */
public final class UltramanTransformState
{
    public static final int POSE_TICKS = 60;
    public static final int TRANSITION_TICKS = 160;
    /** Final 115.2-block stature: exactly twice the first prototype. */
    public static final float TARGET_SCALE = 64.0F;
    private static final String TAG_TARGET = "ProjectSeeleUltramanTarget";
    private static final String TAG_FROM = "ProjectSeeleUltramanFrom";
    private static final String TAG_START = "ProjectSeeleUltramanStart";

    private UltramanTransformState() {}

    public static boolean targetActive(ServerPlayer player)
    {
        return player.getPersistentData().getBoolean(TAG_TARGET);
    }

    public static boolean hasBetaCapsule(ServerPlayer player)
    {
        return player.getMainHandItem().is(ModItems.BETA_CAPSULE.get());
    }

    public static float scale(ServerPlayer player, float partialTick)
    {
        if (!player.getPersistentData().contains(TAG_START))
        {
            return 1.0F;
        }
        float from = player.getPersistentData().getFloat(TAG_FROM);
        float target = targetActive(player) ? TARGET_SCALE : 1.0F;
        long elapsed = player.level().getGameTime()
                - player.getPersistentData().getLong(TAG_START);
        float adjusted = targetActive(player)
                ? elapsed + partialTick - POSE_TICKS
                : elapsed + partialTick;
        float t = Mth.clamp(adjusted / TRANSITION_TICKS, 0.0F, 1.0F);
        float smooth = t * t * (3.0F - 2.0F * t);
        return Mth.lerp(smooth, from, target);
    }

    public static boolean hayataPose(ServerPlayer player)
    {
        return targetActive(player)
                && player.level().getGameTime()
                - player.getPersistentData().getLong(TAG_START) < POSE_TICKS;
    }

    public static boolean toggle(ServerPlayer player)
    {
        float current = scale(player, 0.0F);
        boolean active = !targetActive(player);
        player.getPersistentData().putBoolean(TAG_TARGET, active);
        player.getPersistentData().putFloat(TAG_FROM, current);
        player.getPersistentData().putLong(TAG_START,
                player.level().getGameTime());
        player.refreshDimensions();
        sync(player, current);
        return active;
    }

    public static boolean needsTick(ServerPlayer player)
    {
        if (!player.getPersistentData().contains(TAG_START))
        {
            return false;
        }
        long elapsed = player.level().getGameTime()
                - player.getPersistentData().getLong(TAG_START);
        return targetActive(player)
                || elapsed <= TRANSITION_TICKS + POSE_TICKS;
    }

    public static void finishShrink(ServerPlayer player)
    {
        if (targetActive(player)
                || !player.getPersistentData().contains(TAG_START))
        {
            return;
        }
        long elapsed = player.level().getGameTime()
                - player.getPersistentData().getLong(TAG_START);
        if (elapsed > TRANSITION_TICKS)
        {
            clear(player);
        }
    }

    public static void clear(ServerPlayer player)
    {
        player.getPersistentData().remove(TAG_TARGET);
        player.getPersistentData().remove(TAG_FROM);
        player.getPersistentData().remove(TAG_START);
        player.refreshDimensions();
        sync(player, 1.0F);
    }

    public static void syncTo(ServerPlayer viewer, ServerPlayer subject)
    {
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.PLAYER.with(() -> viewer),
                new ClientboundUltramanStatePacket(subject.getId(),
                        targetActive(subject), scale(subject, 0.0F),
                        hayataPose(subject)));
    }

    private static void sync(ServerPlayer player, float current)
    {
        SeeleNetwork.CHANNEL.send(
                PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> player),
                new ClientboundUltramanStatePacket(player.getId(),
                        targetActive(player), current, hayataPose(player)));
    }
}
