package com.projectseele.world;

import com.google.gson.JsonParser;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraft.world.phys.AABB;
import java.nio.file.Files;
import java.util.Map;
import java.util.WeakHashMap;

/** Save-local authority for the explicitly rebuilt R04 containment chamber. */
public final class TvDetailR04Layout
{
    private static final Map<MinecraftServer,Boolean> ACTIVE=new WeakHashMap<>();
    public static boolean active(ServerLevel level)
    {
        return ACTIVE.computeIfAbsent(level.getServer(),s->{
            var p=s.getWorldPath(LevelResource.ROOT).resolve("regional_tv_detail_r04.json");
            if(!Files.isRegularFile(p))return false;
            try{return JsonParser.parseString(Files.readString(p)).getAsJsonObject().get("dogma_complete").getAsBoolean();}
            catch(Exception e){throw new IllegalStateException("Invalid R04 facility marker",e);}
        });
    }
    public static BlockPos specimenAnchor(){return new BlockPos(30,-600,355);}
    public static AABB specimenBounds(){return new AABB(-38,-631,260,100,-530,403);}
}
