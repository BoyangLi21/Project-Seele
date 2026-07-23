package com.projectseele.network;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.visual.GeoFrontCommands;
import com.projectseele.world.IntegratedNervMapBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.PacketDistributor;

/**
 * Authenticated low-resolution cockpit frame uploaded by the actual EVA pilot.
 * The server never decodes image data; it validates and relays only to players
 * physically present in the NERV command area.
 */
public final class ServerboundEvaVideoFramePacket
{
    public static final int FRAME_WIDTH = 160;
    public static final int FRAME_HEIGHT = 90;
    public static final int MAX_FRAME_BYTES = 96 * 1024;
    private static final int MIN_FRAME_INTERVAL_TICKS = 4;
    public static final int FEED_ACTIVE_TICKS = 60;
    private static final Map<UUID, Long> LAST_ACCEPTED_TICK = new HashMap<>();
    private static final long[] LAST_VARIANT_TICK = {
            Long.MIN_VALUE / 2, Long.MIN_VALUE / 2, Long.MIN_VALUE / 2
    };
    private static final long[] LAST_HUMAN_VARIANT_TICK = {
            Long.MIN_VALUE / 2, Long.MIN_VALUE / 2, Long.MIN_VALUE / 2
    };
    private static final byte[] PNG_SIGNATURE = {
            (byte) 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A
    };

    private final int variant;
    private final byte[] png;

    public ServerboundEvaVideoFramePacket(int variant, byte[] png)
    {
        this.variant = variant;
        this.png = png;
    }

    public ServerboundEvaVideoFramePacket(FriendlyByteBuf buffer)
    {
        this(buffer.readUnsignedByte(),
                buffer.readByteArray(MAX_FRAME_BYTES));
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeByte(this.variant);
        buffer.writeByteArray(this.png);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        ServerPlayer sender = context.getSender();
        if (sender != null)
        {
            context.enqueueWork(() -> relay(sender));
        }
        context.setPacketHandled(true);
    }

    private void relay(ServerPlayer sender)
    {
        if (!(sender.getVehicle() instanceof EvaUnit01Entity eva)
                || !eva.isAlive() || eva.getUnitVariant() != this.variant
                || eva.getFirstPassenger() != sender
                || this.variant < EvaUnit01Entity.UNIT_00
                || this.variant > EvaUnit01Entity.UNIT_02
                || !validPng(this.png))
        {
            return;
        }

        ServerLevel level = sender.serverLevel();
        if (!level.dimension().equals(GeoFrontCommands.GEOFRONT))
        {
            return;
        }
        long now = level.getGameTime();
        long previous = LAST_ACCEPTED_TICK.getOrDefault(
                sender.getUUID(), Long.MIN_VALUE / 2);
        if (now - previous < MIN_FRAME_INTERVAL_TICKS)
        {
            return;
        }
        boolean acquired = !isFeedActive(level, this.variant);
        LAST_ACCEPTED_TICK.put(sender.getUUID(), now);
        LAST_VARIANT_TICK[this.variant] = now;
        LAST_HUMAN_VARIANT_TICK[this.variant] = now;

        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        AABB commandArea = new AABB(
                origin.getX() - 72.0D, origin.getY() - 35.0D,
                origin.getZ() - 50.0D,
                origin.getX() + 73.0D, origin.getY() + 91.0D,
                origin.getZ() + 111.0D);
        ClientboundEvaVideoFramePacket outgoing =
                new ClientboundEvaVideoFramePacket(this.variant, this.png);
        int viewers = 0;
        for (ServerPlayer viewer : level.players())
        {
            if (commandArea.contains(viewer.position()))
            {
                SeeleNetwork.CHANNEL.send(
                        PacketDistributor.PLAYER.with(() -> viewer), outgoing);
                viewers++;
            }
        }
        if (acquired)
        {
            ProjectSeele.LOGGER.info(
                    "NERV cockpit video uplink acquired: eva={} pilot={} viewers={}",
                    this.variant, sender.getGameProfile().getName(), viewers);
        }
    }

    public static boolean isFeedActive(ServerLevel level, int variant)
    {
        if (variant < EvaUnit01Entity.UNIT_00
                || variant > EvaUnit01Entity.UNIT_02)
        {
            return false;
        }
        long now = level.getGameTime();
        long accepted = LAST_VARIANT_TICK[variant];
        return now >= accepted && now - accepted <= FEED_ACTIVE_TICKS;
    }
    public static boolean isHumanFeedActive(ServerLevel level, int variant)
    {
        if (variant < EvaUnit01Entity.UNIT_00
                || variant > EvaUnit01Entity.UNIT_02)
        {
            return false;
        }
        long now = level.getGameTime();
        long accepted = LAST_HUMAN_VARIANT_TICK[variant];
        return now >= accepted && now - accepted <= FEED_ACTIVE_TICKS;
    }

    public static boolean hasCommandViewers(ServerLevel level)
    {
        AABB area = commandArea();
        return level.players().stream().anyMatch(
                viewer -> area.contains(viewer.position()));
    }

    /** Relays a server-sampled view only while no real pilot owns this feed. */
    public static void relayTrainingFrame(ServerLevel level, int variant,
                                          byte[] png)
    {
        if (!level.dimension().equals(GeoFrontCommands.GEOFRONT)
                || variant < EvaUnit01Entity.UNIT_00
                || variant > EvaUnit01Entity.UNIT_02
                || isHumanFeedActive(level, variant) || !validPng(png))
        {
            return;
        }
        LAST_VARIANT_TICK[variant] = level.getGameTime();
        ClientboundEvaVideoFramePacket outgoing =
                new ClientboundEvaVideoFramePacket(variant, png);
        for (ServerPlayer viewer : level.players())
        {
            if (commandArea().contains(viewer.position()))
            {
                SeeleNetwork.CHANNEL.send(
                        PacketDistributor.PLAYER.with(() -> viewer), outgoing);
            }
        }
    }

    private static AABB commandArea()
    {
        BlockPos origin = IntegratedNervMapBuilder.GEOFRONT_ORIGIN;
        return new AABB(origin.getX() - 72.0D, origin.getY() - 35.0D,
                origin.getZ() - 50.0D, origin.getX() + 73.0D,
                origin.getY() + 91.0D, origin.getZ() + 111.0D);
    }

    private static boolean validPng(byte[] data)
    {
        if (data == null || data.length < 24
                || data.length > MAX_FRAME_BYTES)
        {
            return false;
        }

        for (int index = 0; index < PNG_SIGNATURE.length; index++)
        {
            if (data[index] != PNG_SIGNATURE[index])
            {
                return false;
            }
        }
        if (readBigEndianInt(data, 16) != FRAME_WIDTH
                || readBigEndianInt(data, 20) != FRAME_HEIGHT)
        {
            return false;
        }
        return true;
    }

    private static int readBigEndianInt(byte[] data, int offset)
    {
        return (data[offset] & 0xFF) << 24
                | (data[offset + 1] & 0xFF) << 16
                | (data[offset + 2] & 0xFF) << 8
                | data[offset + 3] & 0xFF;
    }
}
