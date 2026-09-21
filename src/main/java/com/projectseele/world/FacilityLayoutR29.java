package com.projectseele.world;

import com.google.gson.JsonParser;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import java.nio.file.Files;
import java.util.Map;
import java.util.WeakHashMap;

public final class FacilityLayoutR29
{
    private static final Map<MinecraftServer, Boolean> ACTIVE = new WeakHashMap<>();
    public static boolean active(MinecraftServer server)
    {
        return ACTIVE.computeIfAbsent(server, key ->
        {
            var file=server.getWorldPath(LevelResource.ROOT).resolve("eva_facility_r29.json");
            if(!Files.isRegularFile(file))return false;
            try
            {
                var data=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                if(data.get("hangar_gate_top").getAsInt()!=-370)throw new IllegalArgumentException("Unexpected gate height");
                return data.get("installed").getAsBoolean();
            }
            catch(Exception error){throw new IllegalStateException("Invalid R29 facility manifest",error);}
        });
    }
    private FacilityLayoutR29() {}
}
