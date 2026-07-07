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
    public static final int ACTION_SMASH = 5;
    public static final int ACTION_CROUCH_START = 6;
    public static final int ACTION_CROUCH_STOP = 7;
    public static final int ACTION_SPRINT_START = 8;
    public static final int ACTION_SPRINT_STOP = 9;
    public static final int ACTION_JUMP = 10;
    public static final int ACTION_EXIT = 11;
    public static final int ACTION_STOMP = 12;
    public static final int ACTION_TOGGLE_PRONE = 13;

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
                case ACTION_SMASH -> eva.smashAttack(sender);
                case ACTION_CHARGE_START -> eva.setChargingHeld(true);
                case ACTION_CHARGE_STOP -> eva.releaseCannon(sender);
                case ACTION_CROUCH_START -> eva.setPilotCrouching(sender, true);
                case ACTION_CROUCH_STOP -> eva.setPilotCrouching(sender, false);
                case ACTION_SPRINT_START -> eva.setPilotSprinting(sender, true);
                case ACTION_SPRINT_STOP -> eva.setPilotSprinting(sender, false);
                case ACTION_JUMP -> eva.pilotJump(sender);
                case ACTION_EXIT -> eva.exitEva(sender);
                case ACTION_STOMP -> eva.stompAttack(sender);
                case ACTION_TOGGLE_PRONE -> eva.toggleProne(sender);
                default -> { }
            }
        }
        ctx.get().setPacketHandled(true);
    }
}
