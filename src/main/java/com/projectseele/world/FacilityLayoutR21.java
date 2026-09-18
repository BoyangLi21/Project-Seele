package com.projectseele.world;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;
import java.nio.file.Files;
/** R21's authored civil layout replaces the old public-pavilion generator. */
public final class FacilityLayoutR21
{
    public static final BlockPos ARMAMENT=new BlockPos(120,80,-36);
    public static boolean active(ServerLevel level){return Files.isRegularFile(level.getServer().getWorldPath(LevelResource.ROOT).resolve("battlefield_r21.json"));}
    private FacilityLayoutR21(){}
}
