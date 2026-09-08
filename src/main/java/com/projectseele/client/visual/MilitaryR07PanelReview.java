package com.projectseele.client.visual;

import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.world.*;
import net.minecraft.client.Minecraft;
import net.minecraft.core.*;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.level.*;
import net.minecraft.world.level.block.ButtonBlock;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.*;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Real right-click packet test; protects the operator and restores the defense switch. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID,value=Dist.CLIENT)
public final class MilitaryR07PanelReview
{
    private static final boolean ENABLED="r07-panel".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final BlockPos BUTTON=new BlockPos(6400,76,-6545);
    private static int age,ticks,ending;private static volatile boolean ready,finished;
    private static boolean oldDefense,oldFlying,oldPause;private static Vec3 oldPos;private static float yaw,pitch;
    private static ResourceKey<Level> dimension;private static GameType mode;
    private static final JsonObject report=new JsonObject();
    @SubscribeEvent public static void tick(TickEvent.ClientTickEvent event)
    {
        if(!ENABLED||event.phase!=TickEvent.Phase.END)return;Minecraft mc=Minecraft.getInstance();var server=mc.getSingleplayerServer();
        if(finished){if(++ending>40){mc.options.pauseOnLostFocus=oldPause;mc.stop();}return;}
        if(mc.player==null||server==null)return;
        Path world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))throw new IllegalStateException("R07 panel world boundary");
        if(++age==100)
        {
            oldPause=mc.options.pauseOnLostFocus;mc.options.pauseOnLostFocus=false;
            server.execute(()->{
                var player=server.getPlayerList().getPlayers().get(0);oldPos=player.position();yaw=player.getYRot();pitch=player.getXRot();dimension=player.level().dimension();mode=player.gameMode.getGameModeForPlayer();oldFlying=player.getAbilities().flying;
                var level=server.getLevel(FacilitySchemaV2.DIMENSION);oldDefense=MilitaryR07Director.state(level).defense;
                player.setGameMode(GameType.CREATIVE);player.teleportTo(level,6400.5,75,-6548.5,0,0);player.getAbilities().flying=false;player.onUpdateAbilities();ready=true;
            });
        }
        if(!ready)return;ticks++;
        if(ticks==80||ticks==140)mc.gameMode.useItemOn(mc.player,InteractionHand.MAIN_HAND,new BlockHitResult(Vec3.atCenterOf(BUTTON),Direction.NORTH,BUTTON,false));
        if(ticks==90||ticks==150)
        {
            boolean first=ticks==90;
            server.execute(()->{
                var level=server.getLevel(FacilitySchemaV2.DIMENSION);var data=MilitaryR07Director.state(level);
                boolean passed=data.defense==(first?!oldDefense:oldDefense);
                report.addProperty(first?"first_click_toggles_once":"second_click_restores",passed);
                if(first){report.addProperty("physical_button_pressed",level.getBlockState(BUTTON).getValue(ButtonBlock.POWERED));passed&=report.get("physical_button_pressed").getAsBoolean();}
                if(!passed||!first)
                {
                    if(data.defense!=oldDefense)MilitaryR07Director.request(level,"defense",null);
                    var player=server.getPlayerList().getPlayers().get(0);player.teleportTo(server.getLevel(dimension),oldPos.x,oldPos.y,oldPos.z,yaw,pitch);player.setGameMode(mode);player.getAbilities().flying=oldFlying;player.onUpdateAbilities();player.fallDistance=0;
                    report.addProperty("passed",passed&&report.get("first_click_toggles_once").getAsBoolean()&&report.get("physical_button_pressed").getAsBoolean());
                    try{Files.writeString(world.resolve("r07_panel_review.json"),report.toString());}catch(Exception error){throw new IllegalStateException(error);}
                    ProjectSeele.LOGGER.info("R07 NATIVE PANEL REVIEW {}",report);finished=true;
                }
            });
        }
    }
}
