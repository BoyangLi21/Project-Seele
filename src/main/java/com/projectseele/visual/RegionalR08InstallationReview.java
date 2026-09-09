package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import com.projectseele.world.MilitaryR07Director;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Explicit migration of existing fleet equipment; never creates replacement UUIDs. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class RegionalR08InstallationReview
{
    private static final boolean RECOVER="r08-heli-recover".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final boolean ENABLED=RECOVER||"r08-installations".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r08_installation",Comparator.comparingLong(ChunkPos::toLong),100);
    public static volatile boolean finished;
    private static int age;private static boolean moved;private static JsonObject plan;private static final JsonArray results=new JsonArray();
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("Wrong R08 installation world");
        if(++age<100)return;var level=server.getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            if(plan==null)plan=JsonParser.parseString(Files.readString(world.resolve("r08_equipment_relocation.json"))).getAsJsonObject();
            var state=MilitaryR07Director.state(level);if(!state.commissioned)throw new IllegalStateException("Existing R07 identities required");
            if(age%20==0)for(var row:plan.getAsJsonArray("moves"))for(String key:new String[]{"from","to"})
            {
                var a=row.getAsJsonObject().getAsJsonArray(key);int x=a.get(0).getAsInt()>>4,z=a.get(2).getAsInt()>>4;
                for(int dx=-1;dx<=1;dx++)for(int dz=-1;dz<=1;dz++){ChunkPos c=new ChunkPos(x+dx,z+dz);level.getChunkSource().addRegionTicket(TICKET,c,2,c);level.getChunk(c.x,c.z);}
            }
            if(age<(RECOVER?240:220))return;
            for(var row:plan.getAsJsonArray("moves"))
            {
                var spec=row.getAsJsonObject();String key=spec.get("key").getAsString();UUID id=state.entities.get(key);
                if(id==null)throw new IllegalStateException("Missing identity "+key);
                Entity entity=level.getEntity(id);
                if(entity==null&&RECOVER&&key.equals("vehicle/fleet/4")&&age>=240)
                {
                    CompoundTag tag=net.minecraft.nbt.TagParser.parseTag(Files.readString(world.resolve("r08_ah6_restore.snbt")));
                    if(!tag.getUUID("UUID").equals(id)||!tag.getString("id").equals("superbwarfare:ah_6")||tag.getBoolean("IsWreck"))throw new IllegalStateException("Invalid verified checkpoint restoration");
                    entity=net.minecraft.core.registries.BuiltInRegistries.ENTITY_TYPE.get(new ResourceLocation("superbwarfare:ah_6")).create(level);
                    entity.load(tag);if(!level.addFreshEntity(entity))throw new IllegalStateException("AH6 identity collision");
                    ProjectSeele.LOGGER.info("R08 AH6 restored original UUID at new berth, health={}",tag.getFloat("Health"));
                }
                if(entity==null){if(age>700)throw new IllegalStateException("Existing entity did not load "+key);return;}
                if(entity.isVehicle())throw new IllegalStateException("Occupied equipment "+key);
                var a=spec.getAsJsonArray("to");Vec3 point=new Vec3(a.get(0).getAsDouble(),a.get(1).getAsDouble(),a.get(2).getAsDouble());
                if(!moved)
                {
                    float yaw=spec.get("yaw").getAsFloat();CompoundTag tag=entity.saveWithoutId(new CompoundTag());tag.putFloat("ServerYaw",yaw);
                    net.minecraft.nbt.ListTag positionTag=new net.minecraft.nbt.ListTag();for(double coordinate:new double[]{point.x,point.y,point.z})positionTag.add(net.minecraft.nbt.DoubleTag.valueOf(coordinate));tag.put("Pos",positionTag);
                    entity.load(tag);entity.moveTo(point.x,point.y,point.z,yaw,0);entity.setDeltaMovement(Vec3.ZERO);entity.fallDistance=0;
                    UUID ownerId=state.entities.get("owner/"+key);
                    if(ownerId!=null)
                    {
                        Entity owner=level.getEntity(ownerId);if(owner==null)throw new IllegalStateException("Owner not loaded "+key);owner.setPos(point.x,point.y-1,point.z);
                    }
                }
                else
                {
                    if(entity.distanceToSqr(point)>1.5)throw new IllegalStateException("Relocated equipment drifted "+key+" "+entity.position());
                    UUID owner=state.entities.get("owner/"+key);
                    if(owner!=null&&entity.getClass().getMethod("getOwner").invoke(entity)!=level.getEntity(owner))throw new IllegalStateException("Defense ownership broken "+key);
                    if(RECOVER&&key.equals("vehicle/fleet/4"))
                    {
                        float health=((Number)entity.getClass().getMethod("getHealth").invoke(entity)).floatValue();
                        if(health<250)throw new IllegalStateException("Restored helicopter took unexpected damage "+health+" "+entity.saveWithoutId(new CompoundTag()));
                        for(String defense:new String[]{"vehicle/fleet/1","vehicle/fleet/3"})
                        {
                            Entity gun=level.getEntity(state.entities.get(defense));if(gun!=null&&(Boolean)gun.getClass().getMethod("basicEnemyFilter",Entity.class).invoke(gun,entity))throw new IllegalStateException("Friendly helicopter considered hostile");
                        }
                        if(age%100==0)ProjectSeele.LOGGER.info("R08 AH6 stability health={} position={} age={}",health,entity.position(),age);
                    }
                    JsonObject proof=new JsonObject();proof.addProperty("key",key);proof.addProperty("uuid",id.toString());proof.addProperty("position",entity.position().toString());proof.addProperty("ownerPreserved",true);results.add(proof);
                }
            }
            if(!moved){moved=true;age=180;return;}
            if(RECOVER&&age<980){results.asList().clear();return;}
            if(state.entities.size()!=31)throw new IllegalStateException("Unexpected managed entity count "+state.entities.size());
            JsonObject receipt=new JsonObject();receipt.addProperty("passed",true);receipt.addProperty("managedUUIDs",state.entities.size());receipt.add("relocations",results);Files.writeString(world.resolve("r08_installation_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(receipt));
            ProjectSeele.LOGGER.info("R08 INSTALLATIONS PASS {}",receipt);finished=true;server.halt(false);
        }
        catch(Exception failure)
        {
            ProjectSeele.LOGGER.error("R08 INSTALLATIONS FAILED",failure);try{Files.writeString(world.resolve("r08_installation_failure.txt"),failure.toString());}catch(Exception ignored){}finished=true;server.halt(false);
        }
    }
}
