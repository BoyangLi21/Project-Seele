package com.projectseele;

import com.projectseele.entity.RamielEntity;
import com.projectseele.registry.ModEntities;
import net.minecraftforge.event.entity.EntityAttributeCreationEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.MOD)
public class CommonEvents
{
    @SubscribeEvent
    public static void onEntityAttributeCreation(EntityAttributeCreationEvent event)
    {
        event.put(ModEntities.RAMIEL.get(), RamielEntity.createAttributes().build());
    }
}
