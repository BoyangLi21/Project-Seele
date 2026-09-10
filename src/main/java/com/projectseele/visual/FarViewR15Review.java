package com.projectseele.visual;

import com.projectseele.ProjectSeele;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Four repeatable viewpoints on the copied map; no gameplay geometry is authored. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class FarViewR15Review
{
    public static final boolean ENABLED="r15-farview".equals(System.getProperty("projectseele.regionalBuild",""));
    public record Shot(String name,Vec3 eye,Vec3 target){}
    public static final Shot[] SHOTS={
        new Shot("city_far",new Vec3(-493,160,746),new Vec3(0,90,325)),
        new Shot("geofront_pyramid",new Vec3(-155,-370,492),new Vec3(28,-410,318)),
        new Shot("geofront_lake",new Vec3(-240,-442,360),new Vec3(-560,-468,230)),
        new Shot("command_interior",new Vec3(36,-405.8,276),new Vec3(29,-407.8,283))};
    public static volatile int index=-1,age;
    public static volatile boolean next,finished;
    @SubscribeEvent public static void tick(TickEvent.ServerTickEvent event)
    {
        if(!ENABLED||finished||event.phase!=TickEvent.Phase.END)return;var server=event.getServer();if(server.getPlayerList().getPlayers().isEmpty())return;
        if(!server.getWorldPath(net.minecraft.world.level.storage.LevelResource.ROOT).normalize().getFileName().toString().equals("SEELE_STAFF_REVIEW_R15"))throw new IllegalStateException("Far view requires copied save");
        if(index<0||next)
        {
            next=false;age=0;if(++index>=SHOTS.length){finished=true;return;}var level=server.getLevel(GeoFrontCommands.GEOFRONT);var player=server.getPlayerList().getPlayers().get(0);var s=SHOTS[index];var d=s.target.subtract(s.eye);
            player.setGameMode(net.minecraft.world.level.GameType.SPECTATOR);player.teleportTo(level,s.eye.x,s.eye.y-1.62,s.eye.z,(float)Math.toDegrees(Math.atan2(-d.x,d.z)),(float)-Math.toDegrees(Math.atan2(d.y,d.horizontalDistance())));
            ProjectSeele.LOGGER.info("R15 FAR VIEW {}",s.name);
        }
        age++;
    }
    private FarViewR15Review(){}
}
