package com.projectseele.client;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.SbwStaticShapesR24;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLClientSetupEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import java.util.*;
import java.util.function.Function;

/** Optional drawing-only occlusion; controlled and moving vehicles stay visible. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,bus=Mod.EventBusSubscriber.Bus.MOD,value=Dist.CLIENT)
public final class ClientOcclusionR24
{
    private static Class<?> api;private static Object instance;
    @SubscribeEvent public static void setup(FMLClientSetupEvent event)
    {
        if(!ModList.get().isLoaded("entityculling"))return;
        event.enqueueWork(()->{
            try
            {
                api=Class.forName("dev.tr7zw.entityculling.EntityCullingModBase");instance=api.getField("instance").get(null);
                Function<Entity,Boolean> moving=e->SbwStaticShapesR24.vehicle(e)&&(e.isVehicle()||e.isPassenger()||!e.onGround()
                        ||e.getDeltaMovement().horizontalDistanceSqr()>1e-8||e.getDeltaMovement().y>.001||e.getDeltaMovement().y<-.25
                        ||e.isOnFire()||Math.abs(e.getYRot()-e.yRotO)>.1||Math.abs(e.getXRot()-e.xRotO)>.1);
                api.getMethod("addDynamicEntityWhitelist",Function.class).invoke(instance,moving);
            }
            catch(Exception error){throw new IllegalStateException("Optional occlusion API mismatch",error);}
        });
    }
    public static boolean enabled() throws Exception{return api!=null&&api.getField("enabled").getBoolean(null);}
    public static void enabled(boolean value) throws Exception
    {if(api==null)throw new IllegalStateException("Occlusion mod is not loaded");api.getField("enabled").setBoolean(null,value);}
    public static Map<String,Object> diagnostics()
    {
        if(api==null)return Map.of("loaded",false);
        try
        {
            var result=new TreeMap<String,Object>();result.put("loaded",true);result.put("enabled",enabled());
            Object config=api.getField("config").get(instance);
            for(String key:List.of("tickCulling","skipBlockEntityCulling","tracingDistance","entityWhitelist"))result.put(key,config.getClass().getField(key).get(config));
            for(String key:List.of("renderedEntities","skippedEntities","skippedEntityTicks"))result.put(key,api.getField(key).get(instance));
            return result;
        }
        catch(Exception error){throw new IllegalStateException(error);}
    }
    private ClientOcclusionR24(){}
}
