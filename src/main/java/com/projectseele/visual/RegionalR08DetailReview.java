package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModEntities;
import com.projectseele.world.FacilitySchemaV2;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** One-time, persistent native display members; ordinary play only loads saved entities. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class RegionalR08DetailReview
{
    private static final boolean ENABLED="r08-details".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished;
    private static int age;private static JsonArray members;
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r08_detail",Comparator.comparingLong(ChunkPos::toLong),100);
    private static final class State extends SavedData
    {
        final Map<String,UUID> ids=new LinkedHashMap<>();
        static State load(CompoundTag tag){State s=new State();CompoundTag ids=tag.getCompound("Members");for(String key:ids.getAllKeys())s.ids.put(key,ids.getUUID(key));return s;}
        @Override public CompoundTag save(CompoundTag tag){CompoundTag all=new CompoundTag();ids.forEach(all::putUUID);tag.put("Members",all);return tag;}
    }
    private static ListTag floats(JsonArray array)
    {ListTag tag=new ListTag();for(var x:array)tag.add(FloatTag.valueOf(x.getAsFloat()));return tag;}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("Wrong R08 detail world");
        if(++age<100)return;var level=server.getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            if(members==null)members=JsonParser.parseString(Files.readString(world.resolve("r08_native_details.json"))).getAsJsonObject().getAsJsonArray("members");
            var state=level.getDataStorage().computeIfAbsent(State::load,State::new,"projectseele_r08_details");
            if(age%20==0)for(var item:members)
            {
                var a=item.getAsJsonObject().getAsJsonArray("position");ChunkPos c=new ChunkPos(a.get(0).getAsInt()>>4,a.get(2).getAsInt()>>4);level.getChunkSource().addRegionTicket(TICKET,c,2,c);level.getChunk(c.x,c.z);
            }
            if(age<180)return;
            for(var item:members)
            {
                String key=item.getAsJsonObject().get("key").getAsString();UUID id=state.ids.get(key);
                if(id!=null&&level.getEntity(id)==null){if(age>600)throw new IllegalStateException("Saved detail did not load "+key);return;}
            }
            JsonArray proof=new JsonArray();
            for(var item:members)
            {
                var spec=item.getAsJsonObject();String key=spec.get("key").getAsString();UUID id=state.ids.getOrDefault(key,UUID.nameUUIDFromBytes(("seele/r08/detail/"+key).getBytes(StandardCharsets.UTF_8)));
                Entity e=level.getEntity(id);boolean fresh=e==null;if(fresh)e=ModEntities.INDUSTRIAL_MEMBER.get().create(level);if(e==null)throw new IllegalStateException("Native display creation");
                CompoundTag tag=new CompoundTag();tag.putUUID("UUID",id);tag.putBoolean("NoGravity",true);tag.putBoolean("Invulnerable",true);tag.putFloat("view_range",4F);tag.putFloat("width",0);tag.putFloat("height",0);tag.putFloat("shadow_radius",0);tag.putInt("interpolation_duration",0);
                var block=new ResourceLocation(spec.get("block").getAsString());if(!BuiltInRegistries.BLOCK.containsKey(block))throw new IllegalStateException("Missing display block "+block);tag.put("block_state",NbtUtils.writeBlockState(BuiltInRegistries.BLOCK.get(block).defaultBlockState()));
                CompoundTag transform=new CompoundTag();transform.put("scale",floats(spec.getAsJsonArray("scale")));transform.put("left_rotation",floats(spec.getAsJsonArray("rotation")));transform.put("translation",floats(spec.getAsJsonArray("translation")));ListTag identity=new ListTag();for(float f:new float[]{0,0,0,1})identity.add(FloatTag.valueOf(f));transform.put("right_rotation",identity);tag.put("transformation",transform);
                e.load(tag);var pos=spec.getAsJsonArray("position");e.moveTo(pos.get(0).getAsDouble(),pos.get(1).getAsDouble(),pos.get(2).getAsDouble(),0,0);e.addTag("seele_r08_industrial_member");
                if(fresh&&!level.addFreshEntity(e))throw new IllegalStateException("Duplicate display identity "+key);state.ids.put(key,id);state.setDirty();
                JsonObject row=new JsonObject();row.addProperty("key",key);row.addProperty("uuid",id.toString());proof.add(row);
            }
            JsonObject result=new JsonObject();result.addProperty("passed",true);result.addProperty("members",proof.size());result.add("identities",proof);Files.writeString(world.resolve("r08_detail_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(result));
            ProjectSeele.LOGGER.info("R08 DETAIL PASS members={}",proof.size());finished=true;server.halt(false);
        }
        catch(Exception failure)
        {
            ProjectSeele.LOGGER.error("R08 DETAIL FAILED",failure);try{Files.writeString(world.resolve("r08_detail_failure.txt"),failure.toString());}catch(Exception ignored){}finished=true;server.halt(false);
        }
    }
}
