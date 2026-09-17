package com.projectseele.visual;
import com.google.gson.*;
import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import com.projectseele.registry.ModBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Real liquid and collision-gate cycle in the empty future airframe bay. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class UNAnnexR20Review
{
    private static final boolean ENABLED="r20-civil-annex".equals(System.getProperty("projectseele.regionalBuild",""));
    private static int stage,ticks;private static boolean done;private static final JsonObject checks=new JsonObject();
    private static void check(String key,boolean result){checks.addProperty(key,result);if(!result)throw new IllegalStateException(key);}
    private static int fluid(ServerLevel l){int n=0;for(var p:BlockPos.betweenClosed(6266,77,-6226,6298,120,-6137))if(l.getBlockState(p).is(ModBlocks.LCL_BLOCK.get()))n++;return n;}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent e)
    {
        if(!ENABLED||done||!RegionalSpatialAuditDriver.done||e.phase!=TickEvent.Phase.END)return;var w=e.getServer().getWorldPath(LevelResource.ROOT).normalize();var l=e.getServer().getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            check("isolated_review_world",w.getFileName().toString().equals("SEELE_R20_REVIEW"));if(++ticks>2200)throw new IllegalStateException("Annex cycle timeout "+stage);
            if(stage==0)
            {
                for(int x=6224>>4;x<=6340>>4;x++)for(int z=-6288>>4;z<=-6135>>4;z++)l.getChunk(x,z);
                check("installed",UNAnnexR20.installed(l));check("initial_lcl",fluid(l)>120000);UNAnnexR20.request(l,"drain",null);stage++;return;
            }
            var s=UNAnnexR20.state(l);
            if(stage==1&&s.phase==MilitaryR07Director.Phase.DRY){check("drained",fluid(l)==0);UNAnnexR20.request(l,"door",null);stage++;}
            else if(stage==2&&s.phase==MilitaryR07Director.Phase.OPEN)
            {
                check("open_threshold",l.getBlockState(new BlockPos(6282,80,-6136)).isAir());var obstacle=new ArmorStand(l,6282.5,77,-6135.5);obstacle.setNoGravity(true);l.addFreshEntity(obstacle);UNAnnexR20.request(l,"door",null);check("closing_obstruction_interlock",s.phase==MilitaryR07Director.Phase.OPEN);obstacle.discard();UNAnnexR20.request(l,"door",null);stage++;
            }
            else if(stage==3&&s.phase==MilitaryR07Director.Phase.DRY){check("closed_threshold",l.getBlockState(new BlockPos(6282,80,-6136)).is(net.minecraft.world.level.block.Blocks.BARRIER));UNAnnexR20.request(l,"fill",null);stage++;}
            else if(stage==4&&s.phase==MilitaryR07Director.Phase.WET){check("refilled",fluid(l)>120000);check("model_remains_deferred",l.getEntitiesOfClass(com.projectseele.entity.EvaUnit01Entity.class,new net.minecraft.world.phys.AABB(6224,76,-6288,6340,161,-6135)).isEmpty());Files.writeString(w.resolve("r20_annex_pass.json"),checks.toString());done=true;e.getServer().halt(false);}
        }
        catch(Exception failure){ProjectSeele.LOGGER.error("R20 annex review failed",failure);try{Files.writeString(w.resolve("r20_annex_failure.txt"),failure+"\n"+checks);}catch(Exception ignored){}done=true;e.getServer().halt(false);}
    }
    private UNAnnexR20Review(){}
}
