package com.projectseele.client;

import com.projectseele.network.ClientboundCombatBodyPose;
import com.projectseele.physics.CombatBodyDynamics;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.LivingEntity;

public final class CombatBodyClient
{
    public static void receive(ClientboundCombatBodyPose packet)
    {
        var level=Minecraft.getInstance().level;if(level==null)return;
        if(level.getEntity(packet.id()) instanceof LivingEntity entity&&entity.getUUID().equals(packet.uuid()))CombatBodyDynamics.receive(entity,packet);
    }
    private CombatBodyClient(){}
}
