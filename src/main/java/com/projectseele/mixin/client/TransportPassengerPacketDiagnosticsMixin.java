package com.projectseele.mixin.client;

import com.projectseele.ProjectSeele;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.ClientboundPlayerPositionPacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientPacketListener.class)
public abstract class TransportPassengerPacketDiagnosticsMixin
{
    @Inject(method="handleMovePlayer",at=@At("HEAD"))
    private void projectSeele$traceCorrection(ClientboundPlayerPositionPacket packet,CallbackInfo callback)
    {
        if(!System.getProperty("projectseele.regionalBuild","").contains("riding")||!Minecraft.getInstance().isSameThread())return;
        ProjectSeele.LOGGER.info("TRANSIT CLIENT POSITION PACKET ({}, {}, {}) relative={}",packet.getX(),packet.getY(),packet.getZ(),packet.getRelativeArguments());
    }
}
