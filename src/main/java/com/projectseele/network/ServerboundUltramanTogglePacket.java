package com.projectseele.network;

import com.projectseele.world.UltramanTransformState;
import java.util.function.Supplier;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;

/** Requests a Beta Capsule transformation while the player is unmounted. */
public final class ServerboundUltramanTogglePacket
{
    public ServerboundUltramanTogglePacket() {}
    public ServerboundUltramanTogglePacket(FriendlyByteBuf buffer) {}
    public void encode(FriendlyByteBuf buffer) {}

    public void handle(Supplier<NetworkEvent.Context> supplier)
    {
        NetworkEvent.Context context = supplier.get();
        context.enqueueWork(() ->
        {
            ServerPlayer player = context.getSender();
            if (player == null || player.isPassenger())
            {
                return;
            }
            if (!UltramanTransformState.targetActive(player)
                    && !UltramanTransformState.hasBetaCapsule(player))
            {
                player.displayClientMessage(Component.translatable(
                        "msg.projectseele.beta_capsule_required"), true);
                return;
            }
            boolean active = UltramanTransformState.toggle(player);
            player.displayClientMessage(Component.translatable(active
                    ? "msg.projectseele.ultraman_on"
                    : "msg.projectseele.ultraman_off"), true);
        });
        context.setPacketHandled(true);
    }
}
