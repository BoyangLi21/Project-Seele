package com.projectseele.visual;

import com.google.gson.*;
import com.projectseele.ProjectSeele;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.level.storage.loot.*;
import net.minecraft.world.level.storage.loot.parameters.*;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;

/** Exercise the actual SBW reward and held-book use on the isolated review. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class VehicleManualR24Review
{
    private static final boolean SERVER_ONLY="r24-vehicle-manual-server".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final boolean ENABLED=SERVER_ONLY||"r24-vehicle-manual".equals(System.getProperty("projectseele.regionalBuild",""));
    public static final ResourceLocation BOOK=new ResourceLocation("superbwarfare","superb_warfare_manual");
    public static volatile boolean ready,clientDone,finished;public static volatile String clientError="";
    private static int age,slot;private static ServerPlayer player;private static ListTag inventory;private static GameType mode;private static boolean flying;
    private static net.minecraft.world.item.ItemStack reward(ServerPlayer user)
    {
        var params=new LootParams.Builder(user.serverLevel()).withParameter(LootContextParams.THIS_ENTITY,user)
                .withParameter(LootContextParams.ORIGIN,user.position()).create(LootContextParamSets.ADVANCEMENT_REWARD);
        var result=user.server.getLootData().getLootTable(new ResourceLocation("superbwarfare","grant_manual")).getRandomItems(params);
        if(result.size()!=1||!BuiltInRegistries.ITEM.getKey(result.get(0).getItem()).toString().equals("patchouli:guide_book")
                ||!BOOK.toString().equals(result.get(0).getOrCreateTag().getString("patchouli:book")))throw new IllegalStateException("Native manual reward missing or wrong");
        return result.get(0);
    }
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END||++age<140)return;
        var server=event.getServer();var world=server.getWorldPath(LevelResource.ROOT).normalize();
        if(!world.getFileName().toString().equals("SEELE_R24_TV_REVIEW"))throw new IllegalStateException("Wrong manual review world");
        if(SERVER_ONLY)
        {
            String error="";
            try{var level=server.getLevel(com.projectseele.world.FacilitySchemaV2.DIMENSION);reward(net.minecraftforge.common.util.FakePlayerFactory.getMinecraft(level));}
            catch(Exception failure){error=failure.toString();}
            try{Files.writeString(world.resolve("r24_vehicle_manual_server_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(java.util.Map.of("passed",error.isEmpty(),"error",error,"dedicated_server",true,"native_loot_reward",error.isEmpty(),"book",BOOK.toString())));}
            catch(Exception failure){ProjectSeele.LOGGER.error("Could not save manual server review",failure);}
            finished=true;server.halt(false);return;
        }
        if(server.getPlayerList().getPlayers().isEmpty())return;
        try
        {
            if(!ready)
            {
                player=server.getPlayerList().getPlayers().get(0);inventory=player.getInventory().save(new ListTag());slot=player.getInventory().selected;
                mode=player.gameMode.getGameModeForPlayer();flying=player.getAbilities().flying;
                var book=reward(player);
                player.setGameMode(GameType.CREATIVE);player.getAbilities().flying=true;player.onUpdateAbilities();
                player.setItemInHand(InteractionHand.MAIN_HAND,book.copy());player.containerMenu.broadcastChanges();ready=true;
                ProjectSeele.LOGGER.info("R24 native vehicle manual reward resolved; waiting for real item use");
            }
            if(clientDone||age>1200)
            {
                if(!clientDone)clientError="Native manual client timeout";
                player.getInventory().load(inventory);player.getInventory().selected=slot;player.setGameMode(mode);player.getAbilities().flying=flying;player.onUpdateAbilities();player.containerMenu.broadcastChanges();
                boolean restored=inventory.equals(player.getInventory().save(new ListTag()));
                var result=new JsonObject();result.addProperty("passed",clientError.isEmpty()&&restored);result.addProperty("error",clientError);result.addProperty("native_loot_reward",true);result.addProperty("player_inventory_restored",restored);
                result.addProperty("book",BOOK.toString());Files.writeString(world.resolve("r24_vehicle_manual_review.json"),new GsonBuilder().setPrettyPrinting().create().toJson(result));finished=true;
            }
        }
        catch(Exception error)
        {
            ProjectSeele.LOGGER.error("R24 manual review failed",error);clientError=error.toString();clientDone=true;
            if(inventory!=null){player.getInventory().load(inventory);player.getInventory().selected=slot;player.setGameMode(mode);player.getAbilities().flying=flying;player.onUpdateAbilities();}
            try{Files.writeString(world.resolve("r24_vehicle_manual_review.json"),new Gson().toJson(java.util.Map.of("passed",false,"error",clientError)));}catch(Exception ignored){}
            finished=true;
        }
    }
    private VehicleManualR24Review(){}
}
