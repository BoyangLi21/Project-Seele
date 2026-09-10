package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.capability.EvaPilotCapability;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.network.protocol.game.ClientboundTeleportEntityPacket;
import net.minecraft.server.level.*;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.state.properties.SlabType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Real driver inputs over measured test geometry, including a narrow prone passage. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class EvaTerrainR11Review
{
    public static final boolean TURN_ONLY="r11-terrain-turn".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=TURN_ONLY||"r11-terrain".equals(System.getProperty("projectseele.regionalBuild",""));
    public static volatile boolean tracked,mounted,finished,jump,runningCase,crouchInput;
    public static volatile int actor,forward,caseIndex=TURN_ONLY?5:0,caseTick;
    public static volatile float heading;
    private static int age,phase,ticks,stalled,wallOverlaps;private static boolean built;
    private static EvaUnit01Entity eva;private static ServerPlayer pilot;private static Vec3 previous;private static double maxVertical;
    private static final String[] NAMES={"street_props","one_block_ascent","two_block_descent_run","slab_run","crouched_steps","prone_passage","moving_jump","diagonal_curbs","prone_incline","rapid_stance_steps"};
    private static final JsonArray results=new JsonArray(),trace=new JsonArray();
    private static void box(ServerLevel l,int x,int y,int z,int xx,int yy,int zz,net.minecraft.world.level.block.state.BlockState state)
    {for(BlockPos p:BlockPos.betweenClosed(x,y,z,xx,yy,zz))l.setBlock(p,state,2);}
    private static void terrain(ServerLevel l)
    {
        l.getGameRules().getRule(GameRules.RULE_DOMOBSPAWNING).set(false,l.getServer());l.getGameRules().getRule(GameRules.RULE_DAYLIGHT).set(false,l.getServer());l.setDayTime(6000);
        for(int c=0;c<NAMES.length;c++)
        {
            if(TURN_ONLY&&c!=5)continue;
            int x=c*96;
            // The copied flat-world settings can also generate villages. Clear
            // the explicitly disposable test lane before authoring each fixture.
            for(BlockPos pos:BlockPos.betweenClosed(x-36,-60,-54,x+36,25,174))if(!l.getBlockState(pos).isAir())l.setBlock(pos,Blocks.AIR.defaultBlockState(),2);
            box(l,x-36,-61,-54,x+36,-61,174,Blocks.GRAY_CONCRETE.defaultBlockState());
            for(int z=-45;z<165;z+=12)box(l,x,-61,z,x,-61,z+5,Blocks.WHITE_CONCRETE.defaultBlockState());
            if(c==0){Block[] props={Blocks.STONE_PRESSURE_PLATE,Blocks.IRON_BARS,Blocks.OAK_FENCE,Blocks.LANTERN,Blocks.WHITE_CARPET};for(int i=0;i<props.length;i++)for(int dx=-9;dx<=9;dx+=3)l.setBlock(new BlockPos(x+dx,-60,10+i*20),props[i].defaultBlockState(),2);}
            if(c==8)for(int z=15;z<155;z++){int h=Math.min(3,(z-15)/36+1);box(l,x-28,-60,z,x+28,-61+h,z,Blocks.STONE.defaultBlockState());}
            if(c==9)for(int z=15;z<145;z+=24)box(l,x-28,-60,z,x+28,-60,z+8,Blocks.SMOOTH_STONE_SLAB.defaultBlockState().setValue(SlabBlock.TYPE,SlabType.BOTTOM));
            if(c==1||c==4)for(int z=15;z<155;z++){int h=Math.min(7,(z-15)/20+1);box(l,x-28,-60,z,x+28,-61+h,z,Blocks.STONE.defaultBlockState());}
            if(c==2)for(int z=-54;z<155;z++){int h=Math.max(0,10-Math.max(0,z)/20*2);if(h>0)box(l,x-28,-60,z,x+28,-61+h,z,Blocks.STONE.defaultBlockState());}
            if(c==3)for(int z=15;z<145;z++)box(l,x-28,-60,z,x+28,-60,z,Blocks.SMOOTH_STONE_SLAB.defaultBlockState().setValue(SlabBlock.TYPE,SlabType.BOTTOM));
            if(c==5){box(l,x-20,-60,10,x-17,-34,145,Blocks.STONE_BRICKS.defaultBlockState());box(l,x+17,-60,10,x+20,-34,145,Blocks.STONE_BRICKS.defaultBlockState());box(l,x-20,-38,10,x+20,-36,145,Blocks.STONE_BRICKS.defaultBlockState());}
            if(c==7)for(int z=5;z<145;z++)for(int dx=-28;dx<=28;dx++)if(Math.floorMod(dx+z,40)<3)l.setBlock(new BlockPos(x+dx,-60,z),Blocks.SMOOTH_STONE_SLAB.defaultBlockState(),2);
        }
    }
    private static void place(ServerLevel l)
    {
        runningCase=false;caseTick=0;forward=0;jump=false;crouchInput=caseIndex==4;wallOverlaps=0;pilot.stopRiding();eva.prepareForMotionLab();eva.setNoGravity(false);eva.moveTo(caseIndex*96+.5,caseIndex==2?-50:-60,-36.5,0,0);eva.yBodyRot=eva.yHeadRot=0;eva.setOnGround(true);eva.setDeltaMovement(Vec3.ZERO);eva.fallDistance=0;
        for(var p:l.players())p.connection.send(new ClientboundTeleportEntityPacket(eva));pilot.teleportTo(l,eva.getX(),eva.getY()+1,-49,0,0);pilot.getFoodData().setFoodLevel(20);actor=eva.getId();tracked=mounted=false;phase=1;ticks=0;stalled=0;maxVertical=0;previous=eva.position();
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty()||++age<80)return;
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_TERRAIN_REVIEW_R11"))throw new IllegalStateException("Terrain test is laboratory-only");ServerLevel l=server.overworld();
        try
        {
            if(!built)
            {
                built=true;pilot=server.getPlayerList().getPlayers().get(0);pilot.stopRiding();pilot.setGameMode(GameType.SURVIVAL);pilot.setHealth(pilot.getMaxHealth());pilot.getCapability(EvaPilotCapability.DATA).ifPresent(c->c.setSynchronization(100));server.setFlightAllowed(true);
                var old=new java.util.ArrayList<net.minecraft.world.entity.Entity>();for(var e:l.getAllEntities())if(e instanceof EvaUnit01Entity)old.add(e);for(var e:old)e.discard();terrain(l);eva=ModEntities.EVA_UNIT01.get().create(l);eva.moveTo(caseIndex*96+.5,-60,-36.5,0,0);l.getChunk(eva.blockPosition());if(!l.addFreshEntity(eva))throw new IllegalStateException("Terrain actor spawn refused");place(l);return;
            }
            ticks++;caseTick=ticks;
            if(phase<3&&ticks%20==0){var c=new ChunkPos(eva.blockPosition());l.getChunkSource().addRegionTicket(net.minecraft.server.level.TicketType.PORTAL,c,2,BlockPos.containing(eva.position()));}
            if(phase==1){if(ticks>25&&tracked){if(!eva.boardFromExternalPlug(pilot,100))throw new IllegalStateException("Terrain test boarding failed");phase=2;ticks=0;}else if(ticks>240)throw new IllegalStateException("Terrain client tracking deadline");return;}
            if(phase==2)
            {
                if(ticks==25){if(caseIndex==4)eva.setPilotCrouching(pilot,true);if(caseIndex==5||caseIndex==8)eva.toggleProne(pilot);if(caseIndex==2||caseIndex==3)eva.setPilotSprinting(pilot,true);}
                if(ticks>70&&mounted){phase=3;ticks=caseTick=0;previous=eva.position();runningCase=true;}return;
            }
            if(caseIndex==9){crouchInput=ticks>=45&&ticks<100||ticks>=220&&ticks<260;if(ticks==100||ticks==160)eva.toggleProne(pilot);}
            forward=1;heading=caseIndex==7?(float)(Math.sin(ticks/90D)*16):caseIndex==5&&ticks>=200&&ticks<260?35:0;jump=caseIndex==6&&ticks>=48&&ticks<53;
            if(caseIndex==5&&eva.rifleStanceLevel(1)>2.9F&&l.getBlockCollisions(eva,eva.getBoundingBox().deflate(.02)).iterator().hasNext())wallOverlaps++;
            double dx=eva.position().subtract(previous).horizontalDistance(),dy=eva.getY()-previous.y;maxVertical=Math.max(maxVertical,Math.abs(dy));if(ticks>35&&dx<.015)stalled++;else stalled=0;previous=eva.position();
            if(ticks%2==0){JsonObject r=new JsonObject();r.addProperty("case",NAMES[caseIndex]);r.addProperty("tick",ticks);r.addProperty("x",eva.getX());r.addProperty("y",eva.getY());r.addProperty("z",eva.getZ());r.addProperty("distance",dx);r.addProperty("ground",eva.onGround());r.addProperty("stance",eva.rifleStanceLevel(1));r.addProperty("jump",eva.getJumpSequence());r.addProperty("yaw",eva.getYRot());r.addProperty("terrain_plane",com.projectseele.entity.EvaTerrainSupport.sample(eva).toString());trace.add(r);}
            boolean passed=eva.getZ()>153;
            if(passed||stalled>65||ticks>1300)
            {
                JsonObject result=new JsonObject();result.addProperty("name",NAMES[caseIndex]);result.addProperty("passed",passed&&wallOverlaps==0);result.addProperty("prone_wall_overlaps",wallOverlaps);result.addProperty("ticks",ticks);result.addProperty("end_z",eva.getZ());result.addProperty("max_vertical_tick",maxVertical);result.addProperty("health",eva.getHealth());results.add(result);ProjectSeele.LOGGER.info("R11 TERRAIN RESULT {}",result);forward=0;jump=false;
                runningCase=false;if(++caseIndex<NAMES.length&&!TURN_ONLY){place(l);return;}
                finish(world,"");
            }
        }
        catch(Exception e){ProjectSeele.LOGGER.error("R11 TERRAIN FAILED",e);finish(world,e.toString());}
    }
    private static void finish(Path world,String error)
    {
        forward=0;jump=false;finished=true;try{JsonObject d=new JsonObject();d.add("cases",results);d.add("trace",trace);d.addProperty("error",error);Files.writeString(world.resolve("r11_terrain_review.json"),d.toString());}catch(Exception ignored){}
    }
}
