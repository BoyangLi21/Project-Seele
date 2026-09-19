package com.projectseele.visual;
import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.FacilitySchemaV2;
import com.mojang.authlib.GameProfile;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
import java.util.UUID;

/** Native collision attempts at unsafe edges, plus actual flat-belt propulsion. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class CirculationR21Review
{
 private static final boolean UN_BAYS="r21-un-edges".equals(System.getProperty("projectseele.regionalBuild",""));
 private static final boolean R25="r25-edges".equals(System.getProperty("projectseele.regionalBuild",""));
 private static final boolean R23=R25||"r23-edges".equals(System.getProperty("projectseele.regionalBuild",""));
 private static final boolean ENABLED=R23||UN_BAYS||"r21-edges".equals(System.getProperty("projectseele.regionalBuild",""));
 private static int age;private static boolean done;
 @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
 {
  if(!ENABLED||done||e.phase!=TickEvent.Phase.END||++age<160)return;
  var world=e.getServer().getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals(R25?"SEELE_R25_REVIEW":R23?"SEELE_R22_REVIEW":"SEELE_R21_REVIEW"))throw new IllegalStateException("Edge audit boundary");
  ServerLevel level=e.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(level==null)return;
  var results=new JsonArray();boolean passed=true;
  try
  {
   var player=FakePlayerFactory.get(level,new GameProfile(UUID.fromString("f3f6c231-62c0-4055-92e1-bfc310002121"),"[R21 edge test]"));player.setGameMode(GameType.SURVIVAL);player.getAbilities().flying=false;player.noPhysics=false;player.setMaxUpStep(.6F);
   double[][] edges={{108.5,-442,-30.5,-1,0},{103.5,-442,-53.5,-1,0},{97.5,-369,-52.5,-1,0},{112.5,-394,-255.5,1,0},{96.5,-394,-255.5,-1,0},{123.5,-442,223.5,1,0},{113.5,-442,223.5,-1,0},{30.5,-367,-276.5,0,1},{30.5,-367,-208.5,0,-1}};
   if(UN_BAYS)edges=new double[][]{{6446.5,127,-6217.5,-1,0},{6438.5,127,-6217.5,1,0},{6446.5,127,-6224.5,0,-1},{6446.5,127,-6215.5,0,1},{6286.5,127,-6217.5,-1,0},{6278.5,127,-6217.5,1,0},{6286.5,127,-6224.5,0,-1},{6286.5,127,-6215.5,0,1}};
   java.util.Set<Integer> liftPortCases=new java.util.HashSet<>();
   if(R23)
   {
    var data=JsonParser.parseString(Files.readString(world.resolve(R25?"r25_guard_cases.json":"r23_guard_cases.json"))).getAsJsonArray();edges=new double[data.size()][5];int row=0;
    for(var value:data){var test=value.getAsJsonObject();var p=test.getAsJsonArray("start");var d=test.getAsJsonArray("direction");if(R25&&test.get("id").getAsString().startsWith("r23/command_lift_closed_landing/"))liftPortCases.add(row);edges[row++]=new double[]{p.get(0).getAsDouble(),p.get(1).getAsDouble(),p.get(2).getAsDouble(),d.get(0).getAsDouble(),d.get(2).getAsDouble()};}
   }
   int edgeIndex=0;
   for(double[] q:edges)
   {
    var start=new Vec3(q[0],q[1],q[2]);loadNeighbours(level,start);player.setPos(start);player.setDeltaMovement(Vec3.ZERO);player.setOnGround(true);player.fallDistance=0;double low=q[1];
    for(int i=0;i<80;i++){player.move(MoverType.SELF,new Vec3(q[3]*.14,-.12,q[4]*.14));low=Math.min(low,player.getY());}
    // A real lift parked here opens its landing. Crossing onto its supported
    // cabin is valid; dropping below the threshold is never valid.
    boolean liftPort=liftPortCases.contains(edgeIndex++);
    boolean ok=low>=q[1]-.2&&(liftPort||player.position().distanceTo(start)<2.5);passed&=ok;var row=new JsonObject();row.addProperty("kind",liftPort?"native_lift_landing_support":"walk_against_edge");row.addProperty("start",start.toString());row.addProperty("actual",player.position().toString());row.addProperty("minimum_y",low);row.addProperty("passed",ok);results.add(row);
   }
   for(int side:UN_BAYS||R23?new int[]{}:new int[]{-1,1})
   {
    var mob=EntityType.ZOMBIE.create(level);var start=new Vec3(-4.5+side,-434.0625,320.5); // floor lanes X=-6 / -4
    if(side==1)start=new Vec3(-3.5,-434.0625,320.5);
    loadNeighbours(level,start);mob.setPos(start);mob.setOnGround(true);mob.setDeltaMovement(Vec3.ZERO);
    for(int i=0;i<50;i++)mob.travel(Vec3.ZERO);
    double delta=mob.getZ()-start.z;boolean ok=side<0?delta< -1:delta>1;passed&=ok;var row=new JsonObject();row.addProperty("kind","native_living_belt");row.addProperty("side",side);row.addProperty("start",start.toString());row.addProperty("actual",mob.position().toString());row.addProperty("passed",ok);results.add(row);mob.discard();
   }
   var report=new JsonObject();report.addProperty("passed",passed);report.add("checks",results);Files.writeString(world.resolve(R25?"r25_edge_physics.json":R23?"r23_edge_physics.json":UN_BAYS?"r21_un_edge_physics.json":"r21_edge_physics.json"),report.toString());ProjectSeele.LOGGER.info("EDGE PHYSICS passed={} cases={}",passed,results.size());
  }
  catch(Exception x){try{Files.writeString(world.resolve("r21_edge_physics_failure.txt"),x.toString());}catch(Exception ignored){}ProjectSeele.LOGGER.error("R21 edge physics audit",x);}
  done=true;e.getServer().halt(false);
 }
 private static void loadNeighbours(ServerLevel level,Vec3 p){int cx=(int)Math.floor(p.x)>>4,cz=(int)Math.floor(p.z)>>4;for(int x=cx-1;x<=cx+1;x++)for(int z=cz-1;z<=cz+1;z++)level.getChunk(x,z);}
 private CirculationR21Review(){}
}
