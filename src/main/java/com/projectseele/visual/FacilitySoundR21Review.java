package com.projectseele.visual;
import com.google.gson.*;
import com.projectseele.ProjectSeele;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.PlayLevelSoundEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import java.nio.file.*;
/** Observe actual server emissions during the native factory/pilot acceptance. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class FacilitySoundR21Review
{
 private static final boolean ENABLED="r21-factory".equals(System.getProperty("projectseele.regionalBuild",""));
 private static final JsonArray EVENTS=new JsonArray();
 @SubscribeEvent public static void sound(PlayLevelSoundEvent e)
 {
  if(!ENABLED||!(e.getLevel() instanceof ServerLevel level)||e.getSound()==null)return;
  var sound=e.getSound().value();if(!sound.getLocation().getNamespace().equals("projectseele"))return;
  var pos=e instanceof PlayLevelSoundEvent.AtPosition p?p.getPosition():e instanceof PlayLevelSoundEvent.AtEntity q?q.getEntity().position():null;if(pos==null)return;
  var r=new JsonObject();r.addProperty("sound",sound.getLocation().toString());r.addProperty("tick",level.getGameTime());r.addProperty("x",pos.x);r.addProperty("y",pos.y);r.addProperty("z",pos.z);r.addProperty("server_range",sound.getRange(e.getNewVolume()));
  var player=level.getServer().getPlayerList().getPlayers().stream().findFirst();player.ifPresent(p->{r.addProperty("pilot_distance",p.position().distanceTo(pos));r.addProperty("within_delivery_range",p.position().distanceTo(pos)<=sound.getRange(e.getNewVolume()));});EVENTS.add(r);
  try{Files.writeString(level.getServer().getWorldPath(LevelResource.ROOT).resolve("r21_sound_events.json"),EVENTS.toString());}catch(Exception x){throw new IllegalStateException(x);}
 }
}
