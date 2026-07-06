package com.projectseele.network;

import java.util.function.Supplier;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.NetworkEvent;

/**
 * Pilot input from the entry plug. The server validates that the sender is
 * actually riding a Unit before dispatching — clients are never trusted.
 */
public class ServerboundEvaControlPacket
{
    public static final int ACTION_CYCLE_WEAPON = 0;
    public static final int ACTION_TOGGLE_AT_FIELD = 1;
    public static final int ACTION_MELEE = 2;
    public static final int ACTION_CHARGE_START = 3;
    public static final int ACTION_CHARGE_STOP = 4;

    public final int action;

    public ServerboundEvaControlPacket(int action)
    {
        this.action = action;
    }

    public ServerboundEvaControlPacket(FriendlyByteBuf buf)
    {
        this(buf.readVarInt());
    }

    public void encode(FriendlyByteBuf buf)
    {
        buf.writeVarInt(this.action);
    }

    public void handle(Supplier<NetworkEvent.Context> ctx)
    {
        ServerPlayer sender = ctx.get().getSender();
        if (sender != null && sender.getVehicle() instanceof EvaUnit01Entity eva)
        {
            switch (this.action)
            {
                case ACTION_CYCLE_WEAPON -> eva.cycleWeapon(sender);
                case ACTION_TOGGLE_AT_FIELD -> eva.toggleAtField(sender);
                case ACTION_MELEE -> eva.meleeAttack(sender);
                case ACTION_CHARGE_START -> eva.setChargingHeld(true);
                case ACTION_CHARGE_STOP -> eva.releaseCannon(sender);
                default -> { }
            }
        }
        ctx.get().setPacketHandled(true);
    }
}
