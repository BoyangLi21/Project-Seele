package com.projectseele.client;

import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.network.ServerboundEntryPlugScrapR31;
import com.projectseele.world.EntryPlugDisposalR31;
import net.minecraft.client.Minecraft;
import net.minecraft.world.InteractionHand;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.InputEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid="projectseele",value=Dist.CLIENT)
public final class EntryPlugScrapClientR31
{
    @SubscribeEvent
    public static void attack(InputEvent.InteractionKeyMappingTriggered event)
    {
        var player=Minecraft.getInstance().player;
        if(!event.isAttack()||player==null||player.isPassenger()||player.isSpectator())return;
        EntryPlugCarrierEntity target=null;double nearest=Double.POSITIVE_INFINITY;
        for(var plug:player.level().getEntitiesOfClass(EntryPlugCarrierEntity.class,player.getBoundingBox().inflate(16)))
        {
            var hit=EntryPlugDisposalR31.hit(player,plug);
            if(hit.isEmpty())continue;double distance=hit.get().distanceToSqr(player.getEyePosition());
            if(distance<nearest){nearest=distance;target=plug;}
        }
        if(target==null)return;
        event.setCanceled(true);event.setSwingHand(false);player.swing(InteractionHand.MAIN_HAND);
        SeeleNetwork.CHANNEL.sendToServer(new ServerboundEntryPlugScrapR31(target.getId()));
    }
    private EntryPlugScrapClientR31() {}
}
