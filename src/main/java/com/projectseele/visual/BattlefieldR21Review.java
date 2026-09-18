package com.projectseele.visual;
import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class BattlefieldR21Review
{
 private static final boolean ENABLED="r21-battlefield".equals(System.getProperty("projectseele.regionalBuild",""));
 private static int age,column;private static boolean done;private static final JsonArray failures=new JsonArray();
 @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
 {
  if(!ENABLED||done||e.phase!=TickEvent.Phase.END)return;var world=e.getServer().getWorldPath(LevelResource.ROOT).normalize();if(!world.getFileName().toString().equals("SEELE_R21_REVIEW"))throw new IllegalStateException("R21 battlefield review boundary");var level=e.getServer().getLevel(FacilitySchemaV2.DIMENSION);if(level==null||++age<160)return;
  try
  {
   var state=BattlefieldR21.state(level);if(!state.hidden||!state.job.isEmpty()){if(age>1500)throw new IllegalStateException("Battlefield cover not settled");return;}
   for(int n=0;n<1024&&column<352*352;n++,column++)
   {
    int x=-144+column%352,z=41+column/352;var p=new BlockPos(x,80,z);level.getChunkAt(p);int top=level.getHeight(Heightmap.Types.MOTION_BLOCKING,x,z);
    if(top!=81||!level.getBlockState(p).isCollisionShapeFullBlock(level,p)){var f=new JsonArray();f.add(x);f.add(z);f.add(top);f.add(level.getBlockState(p).toString());failures.add(f);}
   }
   if(column==352*352){var r=new JsonObject();r.addProperty("columns",column);r.addProperty("runtime_conflicts",state.conflicts);r.addProperty("passed",failures.isEmpty()&&state.conflicts==0);r.add("failures",failures);Files.writeString(world.resolve("r21_battlefield_proof.json"),r.toString());ProjectSeele.LOGGER.info("R21 BATTLEFIELD PROOF {}",r);done=true;e.getServer().halt(false);}
  }
  catch(Exception x){try{Files.writeString(world.resolve("r21_battlefield_failure.txt"),x.toString());}catch(Exception ignored){}done=true;ProjectSeele.LOGGER.error("R21 battlefield audit",x);e.getServer().halt(false);}
 }
}
