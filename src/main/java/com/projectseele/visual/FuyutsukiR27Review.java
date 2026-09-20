package com.projectseele.visual;

import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.NervStaffEntity;
import com.projectseele.world.*;
import net.minecraft.server.level.*;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.Files;

/** Real NPC path, gesture, button dispatch and city movement in the isolated cold copy. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class FuyutsukiR27Review
{
    public static volatile boolean finished;
    private static int age,state,presses,maxDepth;
    private static boolean sawLower,sawRise;
    private static void check(boolean value,String message){if(!value)throw new IllegalStateException(message);}
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!FactoryR20Review.R27||!FactoryR20Review.ready||finished||event.phase!=TickEvent.Phase.END)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        try
        {
            check(world.getFileName().toString().equals("SEELE_R27_REVIEW"),"World boundary");
            check(++age<5000,"City review timeout state="+state);
            ServerLevel level=server.getLevel(FacilitySchemaV2.DIMENSION);
            ServerPlayer player=server.getPlayerList().getPlayers().get(0);
            if(age==1){player.stopRiding();player.setGameMode(net.minecraft.world.level.GameType.CREATIVE);player.teleportTo(level,28.5,-406,276.5,0,0);}
            var id=NervStaffSavedData.get(level).identity("fuyutsuki");
            if(id==null||!(level.getEntity(id) instanceof NervStaffEntity npc))return;
            var origin=IntegratedNervMapBuilder.tokyo3Origin(level);
            int depth=Tokyo3RetractionDirector.depth(level,origin);maxDepth=Math.max(maxDepth,depth);
            if(state>0&&!npc.busy())check(npc.pressCount()>=presses+state,"NPC action ended without physical press, state="+state);
            if(age%80==0)ProjectSeele.LOGGER.info("R27 CITY TRACE state={} npc={} busy={} presses={} depth={}",state,npc.position(),npc.busy(),npc.pressCount(),depth);
            for(String op:new String[]{"city_lower","city_rise"})
            {
                var button=level.getBlockState(NervOperationsConsole.staffControl(level,op,-1));
                if(button.hasProperty(net.minecraft.world.level.block.ButtonBlock.POWERED)&&button.getValue(net.minecraft.world.level.block.ButtonBlock.POWERED))
                {if(op.equals("city_lower"))sawLower=true;else sawRise=true;}
            }
            if(state==0&&age>80)
            {
                check(npc.station().equals(new net.minecraft.core.BlockPos(27,-406,277)),"Wrong commander post");
                check(level.noCollision(npc),"Commander collides with seat");
                check(StaffIntentR24.parse("城市可以降下吗").kind()==StaffIntentR24.Kind.TOPIC,"Question becomes action");
                check(StaffIntentR24.parse("不要城市降下").kind()!=StaffIntentR24.Kind.ACTION,"Negation becomes action");
                check(!StaffAuthorityR25.allows("guard","fuyutsuki","city_lower"),"Guard impersonation");
                check(!StaffAuthorityR25.allows("commander","misato","city_lower"),"Wrong city operator");
                presses=npc.pressCount();check(NervStaffDialogue.converse(player,npc,"城市降下")==1,"Lower request");state=1;
            }
            else if(state==1&&!npc.busy()&&depth>0)
            {
                check(npc.pressCount()==presses+1&&sawLower,"Lower physical press missing");
                check(NervStaffDialogue.converse(player,npc,"城市升起")==1,"Rise request");state=2;
            }
            else if(state==2&&!npc.busy()&&depth==0&&sawRise)
            {
                check(npc.pressCount()==presses+2,"Rise physical press missing");
                JsonObject proof=new JsonObject();proof.addProperty("passed",true);proof.addProperty("uuid",id.toString());proof.addProperty("physical_presses",2);proof.addProperty("max_depth",maxDepth);proof.addProperty("returned_surface",true);proof.addProperty("ticks",age);
                Files.writeString(world.resolve("r27_city_pass.json"),proof.toString());finished=true;
                ProjectSeele.LOGGER.info("R27 CITY PASS {}",proof);
            }
        }
        catch(Exception e)
        {
            ProjectSeele.LOGGER.error("R27 CITY FAILURE",e);
            try{Files.writeString(world.resolve("r27_city_failure.txt"),e.toString());}catch(Exception ignored){}
            FactoryR20Review.finished=true;finished=true;
        }
    }
    private FuyutsukiR27Review(){}
}
