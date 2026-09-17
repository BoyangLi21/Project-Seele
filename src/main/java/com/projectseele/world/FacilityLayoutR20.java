package com.projectseele.world;

import com.google.gson.JsonParser;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import java.nio.file.Files;
import java.util.Map;
import java.util.WeakHashMap;

/** Installed civil coordinates, activated only after the matching offline patch. */
public final class FacilityLayoutR20
{
    private record Layout(boolean enabled,int cageShiftZ,int launchRise){}
    private static final Map<MinecraftServer,Layout> CACHE=new WeakHashMap<>();
    private static Layout layout(MinecraftServer server)
    {
        return CACHE.computeIfAbsent(server,s->{
            var file=s.getWorldPath(LevelResource.ROOT).resolve("eva_facility_r20.json");
            if(!Files.isRegularFile(file))return new Layout(false,0,0);
            try
            {
                var data=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                int dz=data.get("cage_shift_z").getAsInt(),dy=data.get("launch_rise").getAsInt();
                if(dz> -80||dz< -320||dy<16||dy>64)throw new IllegalArgumentException("Unexpected R20 civil frame");
                return new Layout(data.get("installed").getAsBoolean(),dz,dy);
            }
            catch(Exception e){throw new IllegalStateException("R20 facility manifest",e);}
        });
    }
    public static boolean active(MinecraftServer server){return layout(server).enabled();}
    public static int cageShiftZ(MinecraftServer server){return active(server)?layout(server).cageShiftZ():0;}
    public static int launchRise(MinecraftServer server){return active(server)?layout(server).launchRise():0;}
    private FacilityLayoutR20(){}
}
