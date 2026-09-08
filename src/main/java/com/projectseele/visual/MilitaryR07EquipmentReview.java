package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.*;
import net.minecraft.world.Difficulty;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.item.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingHurtEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.*;

/** Uses installed SBW AI and ordinary vehicle input in the disposable laboratory. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class MilitaryR07EquipmentReview
{
    public static final boolean ENABLED="r07-equipment".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean finished;
    public static volatile int stage=-1;
    public static volatile short input;
    private static int age,phaseAge,hits;private static float damage;
    private static ServerPlayer pilot;private static Entity equipment;private static Zombie target;private static ArmorStand owner;
    private static final List<Entity> spawned=new ArrayList<>();private static final JsonArray checks=new JsonArray();
    private static Vec3 initial;private static Difficulty difficulty;
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r07_equipment_review",Comparator.comparingLong(ChunkPos::toLong),80);
    private static void check(String name,boolean pass,String detail)
    {
        JsonObject r=new JsonObject();r.addProperty("name",name);r.addProperty("passed",pass);r.addProperty("detail",detail);checks.add(r);
        if(!pass)throw new IllegalStateException(name+": "+detail);
        ProjectSeele.LOGGER.info("R07 EQUIPMENT PASS {} {}",name,detail);
    }
    @SubscribeEvent public static void hit(LivingHurtEvent event)
    {
        if(ENABLED&&!finished&&event.getEntity()==target)
            ProjectSeele.LOGGER.info("R07 TARGET HURT stage={} source={} amount={}",stage,event.getSource().typeHolder().unwrapKey(),event.getAmount());
        if(ENABLED&&!finished&&event.getEntity()==target&&event.getSource().typeHolder().unwrapKey().map(k->k.location().toString().equals(stage==0?"superbwarfare:projectile_hit":"superbwarfare:laser_static")).orElse(false))
        {hits++;damage+=event.getAmount();}
    }
    private static Entity spawn(ServerLevel level,String id,Vec3 position) throws Exception
    {
        Entity e=BuiltInRegistries.ENTITY_TYPE.get(new ResourceLocation(id)).create(level);if(e==null)throw new IllegalStateException(id);
        CompoundTag tag=new CompoundTag();tag.putInt("Energy",((Number)e.getClass().getMethod("getMaxEnergy").invoke(e)).intValue());
        tag.putFloat("ServerYaw",0);tag.putBoolean("GearUp",false);
        ListTag items=new ListTag();CompoundTag box=new ItemStack(BuiltInRegistries.ITEM.get(new ResourceLocation("superbwarfare:creative_ammo_box"))).save(new CompoundTag());box.putByte("Slot",(byte)0);items.add(box);tag.put("Items",items);
        e.load(tag);e.moveTo(position.x,position.y,position.z,0,0);e.addTag("seele_r07_lab");level.addFreshEntity(e);spawned.add(e);return e;
    }
    private static void defense(ServerLevel level,String id) throws Exception
    {
        double lane=stage==0?-50.5:40.5;
        equipment=spawn(level,id,new Vec3(lane,-60,-70.5));equipment.addTag("seele_r07_defense");
        owner=EntityType.ARMOR_STAND.create(level);CompoundTag tag=new CompoundTag();tag.putBoolean("Marker",true);tag.putBoolean("Invisible",true);tag.putBoolean("NoGravity",true);tag.putBoolean("Invulnerable",true);owner.load(tag);owner.addTag("seele_r07_control_node");owner.setPos(equipment.position());level.addFreshEntity(owner);spawned.add(owner);
        equipment.getClass().getMethod("setOwnerUUID",UUID.class).invoke(equipment,owner.getUUID());equipment.getClass().getMethod("setActive",boolean.class).invoke(equipment,true);
        target=EntityType.ZOMBIE.create(level);target.setPos(lane,-60,-25.5);target.setNoAi(true);target.setPersistenceRequired();target.addTag("seele_r07_lab");target.setItemSlot(EquipmentSlot.HEAD,new ItemStack(Items.IRON_HELMET));level.addFreshEntity(target);spawned.add(target);
        check(id+"/owner",equipment.getClass().getMethod("getOwner").invoke(equipment)==owner,"offline-independent control node");
        check(id+"/friendly_operator",!(Boolean)equipment.getClass().getMethod("basicEnemyFilter",Entity.class).invoke(equipment,pilot),"ordinary survival player excluded by native team filter");
        hits=0;damage=0;
    }
    private static void clear()
    {
        input=0;if(pilot!=null)pilot.stopRiding();for(Entity e:spawned)e.discard();spawned.clear();equipment=null;target=null;owner=null;
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_EVA_FEED_REVIEW_R06"))throw new IllegalStateException("Equipment review is laboratory-only");
        ServerLevel level=server.overworld();
        try
        {
            if(server.getPlayerList().getPlayers().isEmpty()||++age<100)return;
            level.resetEmptyTime();phaseAge++;
            if(age%20==0)for(int x=-10;x<=10;x++)for(int z=-10;z<=10;z++)
            {ChunkPos p=new ChunkPos(x,z);level.getChunkSource().addRegionTicket(TICKET,p,2,p);}
            if(stage<0)
            {
                pilot=server.getPlayerList().getPlayers().get(0);
                if(!pilot.isAlive())pilot=server.getPlayerList().respawn(pilot,false);
                pilot.setHealth(pilot.getMaxHealth());pilot.getFoodData().setFoodLevel(20);pilot.fallDistance=0;
                pilot.stopRiding();pilot.setGameMode(GameType.SURVIVAL);pilot.getInventory().clearContent();pilot.teleportTo(level,-75,-60,-75,0,0);
                difficulty=server.getWorldData().getDifficulty();server.setDifficulty(Difficulty.NORMAL,true);
                server.setFlightAllowed(true);
                for(Entity old:level.getEntities((Entity)null,new net.minecraft.world.phys.AABB(-65,-64,-85,-35,-40,-15),e->e.getTags().contains("seele_r07_defense")||e.getTags().contains("seele_r07_control_node")||e.getTags().contains("seele_r07_lab")||(e instanceof Zombie z&&z.isNoAi()&&z.distanceToSqr(-50.5,-60,-25.5)<4)))old.discard();
                check("existing_lab_floor",!level.getBlockState(new BlockPos(-50,-61,-70)).isAir(),"no terrain written by review");
                stage=0;phaseAge=0;defense(level,"superbwarfare:hpj_11");return;
            }
            if(stage<2)
            {
                if(phaseAge%100==0)ProjectSeele.LOGGER.info("R07 DEFENSE TRACE stage={} weaponPos={} targetPos={} alive={} health={} energy={} clear={} hostile={} ticks={}",stage,equipment.position(),target.position(),target.isAlive(),target.getHealth(),equipment.getClass().getMethod("getEnergy").invoke(equipment),equipment.getClass().getMethod("checkNoClip",Entity.class,Vec3.class).invoke(equipment,target,equipment.position().add(0,1.4,0)),equipment.getClass().getMethod("basicEnemyFilter",Entity.class).invoke(equipment,target),equipment.tickCount);
                if(hits>0)
                {
                    check(stage==0?"hpj11_native_live_fire":"laser_native_live_fire",damage>0,"hits="+hits+", native damage="+damage+", ticks="+phaseAge);
                    clear();stage++;phaseAge=0;
                    if(stage==1){defense(level,"superbwarfare:laser_tower");return;}
                }
                else if(phaseAge>500)throw new IllegalStateException("No native weapon hit: "+equipment.getType()+" target="+equipment.getClass().getMethod("getTargetUUID").invoke(equipment));
                else return;
            }
            if(stage>=2&&stage<=4)
            {
                String type=stage==2?"m_1a_2":stage==3?"ah_6":"j_16";
                if(!pilot.isAlive())throw new IllegalStateException("Laboratory driver died during "+type);
                if(equipment==null)
                {
                    initial=new Vec3(-110.5,-60,-125.5);equipment=spawn(level,"superbwarfare:"+type,initial);
                    pilot.teleportTo(level,-106.5,-60,-125.5,0,0);pilot.setShiftKeyDown(false);
                    var result=equipment.interact(pilot,InteractionHand.MAIN_HAND);
                    check(type+"/native_boarding",pilot.getVehicle()==equipment,result.toString());phaseAge=0;return;
                }
                input=4;
                equipment.getClass().getMethod("processInput",short.class).invoke(equipment,input);
                if(stage==4)equipment.getClass().getMethod("mouseInput",double.class,double.class).invoke(equipment,0D,phaseAge>60&&equipment.getXRot()>-12?-2D:0D);
                if(phaseAge%100==0)ProjectSeele.LOGGER.info("R07 DRIVE TRACE type={} position={} passenger={} pilotAlive={} energy={} health={} input={} power={}",type,equipment.position(),equipment.getFirstPassenger(),pilot.isAlive(),equipment.getClass().getMethod("getEnergy").invoke(equipment),equipment.getClass().getMethod("getHealth").invoke(equipment),equipment.getClass().getMethod("forwardInputDown").invoke(equipment),equipment.getClass().getMethod("getPower").invoke(equipment));
                Vec3 actual=equipment.position();double travel=actual.distanceTo(initial),rise=actual.y-initial.y;
                if(stage==2&&travel>12||stage>2&&rise>5)
                {
                    check(type+"/powered_motion",true,"travel="+travel+", rise="+rise+", ticks="+phaseAge);
                    clear();stage++;phaseAge=0;
                    if(stage>4){finish(level,world,null);return;}
                }
                if(phaseAge>800)throw new IllegalStateException(type+" motion timeout at "+actual+" power="+equipment.getClass().getMethod("getPower").invoke(equipment));
            }
        }
        catch(Exception failure){finish(level,world,failure);}
    }
    private static void finish(ServerLevel level,Path world,Exception failure)
    {
        clear();finished=true;if(difficulty!=null)level.getServer().setDifficulty(difficulty,true);
        if(pilot!=null){pilot.setGameMode(GameType.CREATIVE);pilot.teleportTo(level,0.5,-59,-150.5,0,0);pilot.fallDistance=0;}
        JsonObject report=new JsonObject();report.addProperty("passed",failure==null);report.add("checks",checks);
        if(failure!=null){report.addProperty("failure",failure.toString());ProjectSeele.LOGGER.error("R07 equipment review failed",failure);}
        try{Files.writeString(world.resolve("r07_equipment_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception ignored){}
    }
}
