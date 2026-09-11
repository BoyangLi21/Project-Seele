package com.projectseele.mixin;

import com.projectseele.util.BiomeCornerCache;
import net.minecraft.world.level.biome.BiomeManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Overwrite;

@Mixin(BiomeManager.class)
public abstract class BiomeManagerMixin
{
    /**
     * @author Project SEELE
     * @reason Reuse identical quart-corner offsets without changing biome selection.
     */
    @Overwrite
    private static double getFiddledDistance(long seed,int x,int y,int z,double dx,double dy,double dz)
    {
        return BiomeCornerCache.distance(seed,x,y,z,dx,dy,dz);
    }
}
