package com.projectseele.network;

import java.util.function.Supplier;

import com.projectseele.ProjectSeele;
import com.projectseele.visual.GeoFrontCommands;
import com.projectseele.world.IntegratedNervMapBuilder;
import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.NetworkEvent;

/** Keeps the real player and client chunk window under each GeoFront camera. */
public final class ServerboundGeoFrontCameraPacket
{
    public static final int S20_VIEW_BASE = 100;
    public static final int S20_RESTORE_VIEW = 199;
    private static final double[][] TRACKING_OFFSETS = {
            {-64.0D, 51.5D, -53.0D},
            {-143.5D, 14.5D, -107.5D},
            {-87.5D, 19.5D, 102.5D},
            {-43.0D, 40.0D, -19.0D},
            {0.0D, 22.0D, 65.5D},
            {3.0D, -1.0D, 96.0D},
            {-46.0D, -1.0D, 86.5D},
            {44.5D, -1.0D, 86.5D},
            {-1.0D, -17.75D, -36.0D},
            {42.0D, -58.5D, -26.5D},
            {-5.0D, -117.0D, -0.5D},
            {-41.0D, 11.0D, 6.0D},
            {0.0D, 16.0D, -57.0D},
    };
    private static final double[][] S20_TRACKING_POSITIONS = {
            {80.0D, -414.0D, 330.0D},
            {80.0D, -414.0D, 356.0D},
            {80.0D, -406.0D, 300.0D},
            {130.0D, -441.0D, 273.0D},
            {80.0D, -396.0D, 144.0D},
             {80.0D, -392.0D, 176.0D},
             {80.0D, -394.0D, 176.0D},
             {80.0D, -424.0D, 218.0D},
             {130.0D, -441.0D, 273.0D},
             {130.0D, 81.0D, 273.0D},
     };

    private final int view;

    public ServerboundGeoFrontCameraPacket(int view)
    {
        this.view = view;
    }

    public ServerboundGeoFrontCameraPacket(FriendlyByteBuf buffer)
    {
        this(buffer.readVarInt() - 1);
    }

    public void encode(FriendlyByteBuf buffer)
    {
        buffer.writeVarInt(this.view + 1);
    }

    public void handle(Supplier<NetworkEvent.Context> contextSupplier)
    {
        NetworkEvent.Context context = contextSupplier.get();
        ServerPlayer sender = context.getSender();
        if (sender != null)
        {
            context.enqueueWork(() -> moveCameraWindow(sender));
        }
        context.setPacketHandled(true);
    }

    private void moveCameraWindow(ServerPlayer player)
    {
        // This packet is deliberately inert in normal multiplayer. It exists
        // only for the opt-in unattended capture JVM used by the repository.
        boolean captureEnabled =
                Boolean.getBoolean("projectseele.visualCapture");
        if (!captureEnabled)
        {
            ProjectSeele.LOGGER.warn(
                    "Ignored GeoFront camera tracking packet outside visual capture");
            return;
        }
        ServerLevel level = player.getServer().getLevel(GeoFrontCommands.GEOFRONT);
        if (level == null)
        {
            return;
        }
        if (this.view >= S20_VIEW_BASE)
        {
            if (this.view == S20_RESTORE_VIEW
                    && com.projectseele.world.FacilityWorldPolicy
                    .isS20Rebuild(player.getServer()))
            {
                level.getChunkAt(new BlockPos(28, -430, 340));
                player.stopRiding();
                player.setNoGravity(false);
                player.setDeltaMovement(Vec3.ZERO);
                player.fallDistance = 0.0F;
                player.teleportTo(level, 28.5D, -429.0D, 340.5D,
                        180.0F, 0.0F);
                return;
            }
            int s20View = this.view - S20_VIEW_BASE;
            if (!com.projectseele.world.FacilityWorldPolicy.isS20Rebuild(
                    player.getServer())
                    || s20View < 0
                    || s20View >= S20_TRACKING_POSITIONS.length)
            {
                return;
            }
            double[] position = S20_TRACKING_POSITIONS[s20View];
            movePlayer(level, player, this.view,
                    position[0], position[1], position[2]);
            return;
        }
        BlockPos origin = GeoFrontCommands.ORIGIN;
        if (this.view < 0)
        {
            BlockPos surface = IntegratedNervMapBuilder.TOKYO3_ORIGIN;
            player.setNoGravity(false);
            player.setDeltaMovement(Vec3.ZERO);
            player.fallDistance = 0.0F;
            player.teleportTo(level, surface.getX() + 0.5D,
                    surface.getY() + 4.0D, surface.getZ() + 0.5D,
                    180.0F, 0.0F);
            return;
        }
        if (this.view >= TRACKING_OFFSETS.length)
        {
            return;
        }
        // Track the midpoint, not the client-only camera. This keeps both the
        // lens and its landmark inside the six-chunk performance profile.
        double[] offset = TRACKING_OFFSETS[this.view];
        double x = origin.getX() + offset[0];
        double y = origin.getY() + offset[1];
        double z = origin.getZ() + offset[2];
        movePlayer(level, player, this.view, x, y, z);
    }

    private static void movePlayer(ServerLevel level, ServerPlayer player,
                                   int view, double x, double y, double z)
    {
        level.getChunkAt(BlockPos.containing(x, y, z));
        player.stopRiding();
        player.setNoGravity(true);
        player.setDeltaMovement(Vec3.ZERO);
        player.fallDistance = 0.0F;
        player.teleportTo(level, x, y, z, 180.0F, 0.0F);
        ProjectSeele.LOGGER.info(
                "GeoFront camera tracking: view={} player={} position={},{},{}",
                view, player.getGameProfile().getName(),
                x, y, z);
    }
}
