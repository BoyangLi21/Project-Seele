package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.world.*;
import com.projectseele.registry.ModFluids;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Exercise a real filled pressure vessel, including recovery into a stale wet bay. */
@Mod.EventBusSubscriber(modid="projectseele")
public final class LclContainmentR30Review
{
    private static final boolean ENABLED="r30-lcl".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final TicketType<ChunkPos> TICKET=TicketType.create("r30_lcl",java.util.Comparator.comparingLong(ChunkPos::toLong),300);
    private static int age;private static boolean done;private static BlockPos origin,bed;private static final JsonObject report=new JsonObject();
    private static void check(String name,boolean value){report.addProperty(name,value);if(!value)throw new IllegalStateException(name);}
    private static int outside(ServerLevel l)
    {
        int count=0;for(BlockPos p:BlockPos.betweenClosed(bed.offset(-21,-5,-29),bed.offset(21,45,37)))
        {
            boolean inside=Math.abs(p.getX()-bed.getX())<=19&&Math.abs(p.getZ()-bed.getZ())<=26&&p.getY()>bed.getY()&&p.getY()<=bed.getY()+44;
            if(!inside&&l.getFluidState(p).getFluidType()==ModFluids.LCL_TYPE.get())count++;
        }return count;
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||done||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_FIELD_R30_REVIEW"))throw new IllegalStateException("Wrong LCL review world");
        var l=server.getLevel(FacilitySchemaV2.DIMENSION);if(l==null)return;l.resetEmptyTime();
        origin=RegionalFacilityLayout.evaOrigin(l);bed=EvaHangarBuilder.hangarBed(origin,1);var c=new ChunkPos(bed);l.getChunkSource().addRegionTicket(TICKET,c,4,c);
        try
        {
            if(++age==80)
            {
                report.addProperty("prior_orphan_cells",outside(l));EvaHangarBuilder.drainLclEnvelope(l,origin,1);EvaHangarBuilder.setGate(l,origin,1,false);EvaHangarBuilder.setLclLevel(l,origin,1,44);
            }
            if(age==220)
            {
                report.addProperty("wet_outside_cells",outside(l));check("filled_cage_is_sealed",outside(l)==0);check("real_full_basin",EvaHangarBuilder.lclLevel(l,origin,1)==44);
                // The same gate call is used by return and launch cancellation.
                EvaHangarBuilder.setGate(l,origin,1,true);check("gate_opens_only_after_physical_drain",EvaHangarBuilder.countLclEnvelope(l,origin,1)==0);
            }
            if(age==380)
            {
                report.addProperty("after_flow_ticks_outside_cells",outside(l));check("no_orphan_flow_after_return_gate",outside(l)==0);
                check("no_refilled_dry_basin",EvaHangarBuilder.countLclEnvelope(l,origin,1)==0);report.addProperty("passed",true);finish(l,world);
            }
        }
        catch(Exception e){report.addProperty("passed",false);report.addProperty("error",e.toString());com.projectseele.ProjectSeele.LOGGER.error("LCL native review failed",e);finish(l,world);}
    }
    private static void finish(ServerLevel l,Path world)
    {
        done=true;EvaHangarBuilder.drainLclEnvelope(l,origin,1);EvaHangarBuilder.setGate(l,origin,1,false);
        try{Files.writeString(world.resolve("r30_lcl_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(report));}catch(Exception e){throw new IllegalStateException(e);}l.getServer().halt(false);
    }
    private LclContainmentR30Review(){}
}
