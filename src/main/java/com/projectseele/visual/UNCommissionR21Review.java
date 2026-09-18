package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaPrototypeEntity;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Verify normal commissioning in the installed main save without moving actors. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class UNCommissionR21Review
{
    private static final boolean ENABLED="r21-un-commission".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int age;private static boolean done;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("Commissioning requires installed TV save");
        var level=server.getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
        try
        {
            for(int cx:new int[]{6442,6282})for(int x=cx-48;x<=cx+48;x+=16)for(int z=-6240;z<=-6128;z+=16)
            {var p=new net.minecraft.world.level.ChunkPos(x>>4,z>>4);level.getChunkSource().addRegionTicket(net.minecraft.server.level.TicketType.PORTAL,p,2,new BlockPos(x,77,z));level.getChunk(p.x,p.z);}
            if(++age<100)return;
            var records=new JsonArray();var identities=new HashSet<UUID>();
            var first=MilitaryR07Director.state(level).entities.get("prototype");var second=UNAnnexR20.state(level).unitId;
            if(first==null||second==null)throw new IllegalStateException("Missing commissioned identity");
            for(var id:List.of(first,second))
            {
                if(!(level.getEntity(id) instanceof EvaPrototypeEntity unit))throw new IllegalStateException("Missing saved airframe "+id);
                var plug=UNPlugDirector.capsule(unit);
                if(plug==null||unit.position().distanceTo(unit.homePosition())>3||unit.isVehicle()||!identities.add(id)||!identities.add(plug.getUUID()))throw new IllegalStateException("Independent dock/capsule check failed");
                var row=new JsonObject();row.addProperty("unit","EVA-UN-0"+unit.getUNSerial());row.addProperty("airframe",id.toString());row.addProperty("plug",plug.getUUID().toString());row.addProperty("health",unit.getHealth());row.addProperty("dock",unit.position().toString());records.add(row);
            }
            if(MilitaryR07Director.state(level).phase!=MilitaryR07Director.Phase.WET||UNAnnexR20.state(level).phase!=MilitaryR07Director.Phase.WET)throw new IllegalStateException("Bays are not safely stored");
            var report=new JsonObject();report.addProperty("passed",true);report.add("units",records);Files.writeString(world.resolve("un_commission_r21.json"),report.toString());
            done=true;server.halt(false);
        }
        catch(Exception failure)
        {ProjectSeele.LOGGER.error("R21 UN commissioning verification failed",failure);try{Files.writeString(world.resolve("un_commission_r21_failure.txt"),failure.toString());}catch(Exception ignored){}done=true;server.halt(false);}
    }
    private UNCommissionR21Review(){}
}
