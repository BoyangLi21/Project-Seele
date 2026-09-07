package com.projectseele.client.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModItems;
import com.projectseele.world.FacilitySchemaV2;
import com.projectseele.world.RegionalGatewayDirector;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Real passenger, native whole-car cargo and card interlock checks in the commissioned save. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, value = Dist.CLIENT)
public final class RegionalPassengerChecks
{
    private static final boolean ENABLED = "passengers".equals(System.getProperty("projectseele.regionalBuild",""));
    private static final Map<BlockPos,BlockState> CARGO = new LinkedHashMap<>();
    private static final List<String> TRACE = new ArrayList<>();
    private static boolean entered, moving;
    private static volatile boolean done;
    private static int age, stage, timer, source = 81, target = -466, trips, arrival;
    private static double previousY, maxStep;
    private static ItemStack mainHand, offHand;
    private static GameType gameType;
    private static net.minecraft.world.phys.Vec3 savedPosition;
    private static net.minecraft.resources.ResourceKey<net.minecraft.world.level.Level> savedDimension;
    private static float savedYaw, savedPitch;
    private static boolean savedFlying, savedPause, optionsSaved;
    private static int savedDistance;

    @SubscribeEvent
    public static void client(TickEvent.ClientTickEvent event)
    {
        if (!ENABLED || event.phase != TickEvent.Phase.END) return;
        var mc = Minecraft.getInstance();
        if (!optionsSaved)
        {
            optionsSaved = true;
            savedPause = mc.options.pauseOnLostFocus;
            savedDistance = mc.options.renderDistance().get();
            mc.options.pauseOnLostFocus = false;
            mc.options.renderDistance().set(6);
        }
        if (done)
        {
            mc.options.pauseOnLostFocus = savedPause;
            mc.options.renderDistance().set(savedDistance);
            mc.stop();
        }
    }

    @SubscribeEvent
    public static void server(TickEvent.ServerTickEvent event)
    {
        if (!ENABLED || done || event.phase != TickEvent.Phase.END) return;
        var server = event.getServer();
        if (server.getPlayerList().getPlayers().isEmpty()) return;
        var world = server.getWorldPath(LevelResource.ROOT).normalize();
        if (!world.getFileName().toString().equals("SEELE_TV_WORLD_PREVIEW_20260906"))
            throw new IllegalStateException("Regional passenger checks refuse another world");
        ServerPlayer player = server.getPlayerList().getPlayers().get(0);
        ServerLevel level = server.getLevel(FacilitySchemaV2.DIMENSION);
        try
        {
            require(++age<6000,"passenger review timeout");
            if (!entered)
            {
                entered = true;
                mainHand = player.getMainHandItem().copy(); offHand = player.getOffhandItem().copy(); gameType = player.gameMode.getGameModeForPlayer();
                savedPosition = player.position(); savedDimension = player.level().dimension();
                savedYaw = player.getYRot(); savedPitch = player.getXRot(); savedFlying = player.getAbilities().flying;
                player.setGameMode(GameType.CREATIVE);player.getAbilities().flying=false;player.onUpdateAbilities();
                player.setItemInHand(InteractionHand.MAIN_HAND,ItemStack.EMPTY);player.setItemInHand(InteractionHand.OFF_HAND,ItemStack.EMPTY);
                player.teleportTo(level,-360.5,81,730.5,0,0);
            }
            timer++;
            if (stage==0)
            {
                if (timer<160) return;
                require(RegionalGatewayDirector.active(level),"commissioned gateway enabled");
                require(!RegionalGatewayDirector.swipe(player),"empty hand cannot unlock entry");
                require(level.getBlockState(new BlockPos(-360,82,733)).is(Blocks.GRAY_STAINED_GLASS),"entry remains physically locked");
                log("PASS empty hand denied; entry closed");
                player.setItemInHand(InteractionHand.MAIN_HAND,ModItems.NERV_EMPLOYEE_CARD.get().getDefaultInstance());
                require(RegionalGatewayDirector.swipe(player),"employee card accepted");stage++;timer=0;return;
            }
            if (stage==1)
            {
                if (timer<20)return;
                require(level.getBlockState(new BlockPos(-360,82,733)).isAir(),"valid swipe opens physical gate");
                log("PASS employee card opens entry");
                boolean upper = RegionalGatewayDirector.carAt(level,81), lower = RegionalGatewayDirector.carAt(level,-466);
                require(upper != lower,"one physical car before passenger test");
                source = upper ? 81 : -466; target = upper ? -466 : 81;
                player.teleportTo(level,-359.5,source,750.5,180,0);
                player.fallDistance=0;player.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);player.setOnGround(true);
                stage++;timer=0;return;
            }
            var group=RegionalGatewayDirector.group(level);
            require(group!=null,"native elevator group exists");
            require(group.getCageSizeX()==15 && group.getCageSizeY()==9 && group.getCageSizeZ()==15,"full-size native capture");
            if (moving)
            {
                double step=Math.abs(player.getY()-previousY);previousY=player.getY();maxStep=Math.max(step,maxStep);
                if(timer%10==0)log("SAMPLE player="+player.getY()+" cage="+group.getCurrentY()+" lastCage="+group.getLastY()+" speed="+group.getTargetSpeed()+" noPhysics="+player.noPhysics+" noGravity="+player.isNoGravity());
                require(step<10,"continuous native passenger travel step="+step);
                require(timer<2200,"native elevator travel timeout");
                if(group.isMoving()){arrival=0;return;}
                if(++arrival<55)return;
                require(Math.abs(player.getY()-target)<.6,"passenger arrives at target floor "+player.getY()+" vs "+target);
                BlockPos anchor=group.getCageAnchorBlockPos(target);
                CARGO.forEach((offset,state)->require(level.getBlockState(anchor.offset(offset)).equals(state),"complete floor/roof cargo "+offset));
                for(double d=0;d<=12;d+=.25)
                {
                    double x=-359.5,z=750.5-d;
                    require(level.noCollision(player,new AABB(x-.3,target+.01,z-.3,x+.3,target+1.8,z+.3)),"open arrival passage d="+d);
                    require(!level.getBlockState(BlockPos.containing(x,target-1,z)).isAir(),"supported arrival passage d="+d);
                }
                log("PASS native 15x15x9 lift "+source+" -> "+target+"; passenger, floor, roof and landing retained");
                trips++;source=target;target=source==81?-466:81;timer=0;moving=false;return;
            }
            if(timer<35)return;
            if(trips==2)
            {
                log("COMPLETE roundTrips=1 passengerTrips=2 maxStep="+maxStep);
                Files.writeString(world.resolve("regional_passenger_checks.txt"),String.join("\n",TRACE));
                Files.deleteIfExists(world.resolve("regional_passenger_failure.txt"));
                restore(player,level);done=true;return;
            }
            require(RegionalGatewayDirector.carAt(level,source),"one physical car at source");
            require(Math.abs(player.getY()-source)<.6,"passenger settled inside source car before departure y="+player.getY());
            BlockPos anchor=group.getCageAnchorBlockPos(source);CARGO.clear();
            for(int x=0;x<15;x++)for(int z=0;z<15;z++)for(int y:new int[]{0,8})
            {BlockPos offset=new BlockPos(x,y,z);CARGO.put(offset,level.getBlockState(anchor.offset(offset)));}
            require(RegionalGatewayDirector.request(level,target,player),"native departure accepted");
            previousY=player.getY();moving=true;timer=0;arrival=0;
        }
        catch(Exception exception)
        {
            ProjectSeele.LOGGER.error("REGIONAL PASSENGER CHECKS FAILED stage="+stage,exception);
            try{Files.writeString(world.resolve("regional_passenger_failure.txt"),String.join("\n",TRACE)+"\n"+exception);}catch(Exception ignored){}
            restore(player,level);done=true;
        }
    }

    private static void restore(ServerPlayer player,ServerLevel level)
    {
        if(mainHand!=null)player.setItemInHand(InteractionHand.MAIN_HAND,mainHand);
        if(offHand!=null)player.setItemInHand(InteractionHand.OFF_HAND,offHand);
        if(gameType!=null)player.setGameMode(gameType);
        if(savedPosition!=null)player.teleportTo(player.server.getLevel(savedDimension),savedPosition.x,savedPosition.y,savedPosition.z,savedYaw,savedPitch);
        player.fallDistance=0;player.setDeltaMovement(net.minecraft.world.phys.Vec3.ZERO);
        player.getAbilities().flying=savedFlying;player.onUpdateAbilities();
    }
    private static void require(boolean condition,String reason){if(!condition)throw new IllegalStateException(reason);}
    private static void log(String line){TRACE.add(line);ProjectSeele.LOGGER.info("REGIONAL PASSENGER {}",line);}
}
