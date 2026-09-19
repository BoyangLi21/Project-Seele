package com.projectseele.mixin.client;

import com.projectseele.client.SkySourceScanR24;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.lighting.ChunkSkyLightSources;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.*;

/** Exact sky-column initialization for deep chunks; no LOD or approximate lighting. */
@Mixin(ChunkSkyLightSources.class)
public abstract class ChunkSkySourceR24Mixin
{
    @Shadow @Final private int minY;
    @Shadow @Final private BlockPos.MutableBlockPos mutablePos1;
    @Shadow @Final private BlockPos.MutableBlockPos mutablePos2;
    @Shadow private static boolean isEdgeOccluded(BlockGetter level,BlockPos above,BlockState upper,BlockPos below,BlockState lower){throw new AssertionError();}
    @Unique private ChunkAccess seele$chunk;
    @Unique private byte[] seele$transparentSections;

    @Inject(method="fillFrom",at=@At("HEAD"))
    private void seele$classify(ChunkAccess chunk,CallbackInfo callback)
    {
        seele$chunk=null;seele$transparentSections=null;
    }
    @Redirect(method="fillFrom",at=@At(value="INVOKE",target="Lnet/minecraft/world/level/chunk/ChunkAccess;getHighestFilledSectionIndex()I"))
    private int seele$reuseHighestSection(ChunkAccess chunk)
    {
        int highest=chunk.getHighestFilledSectionIndex();
        if(highest>=0&&SkySourceScanR24.enabled())
        {
            // Classify only sections that a column actually reaches. Reuse
            // the original top-section scan, including entirely empty chunks.
            seele$chunk=chunk;seele$transparentSections=new byte[highest+1];
        }
        return highest;
    }
    @Inject(method="fillFrom",at=@At("RETURN"))
    private void seele$release(ChunkAccess chunk,CallbackInfo callback){seele$chunk=null;seele$transparentSections=null;}

    @Inject(method="findLowestSourceY(Lnet/minecraft/world/level/chunk/ChunkAccess;III)I",at=@At("HEAD"),cancellable=true)
    private void seele$scan(ChunkAccess chunk,int highest,int x,int z,CallbackInfoReturnable<Integer> callback)
    {
        if(seele$chunk!=chunk)return;
        BlockState previous=Blocks.AIR.defaultBlockState();boolean previousClear=true;
        var above=mutablePos1;var below=mutablePos2;
        for(int sectionIndex=highest;sectionIndex>=0;sectionIndex--)
        {
            var section=chunk.getSection(sectionIndex);int base=chunk.getSectionYFromSectionIndex(sectionIndex)<<4;
            // Preserve vanilla's empty-section boundary treatment exactly.
            if(section.hasOnlyAir()){previous=Blocks.AIR.defaultBlockState();previousClear=true;continue;}
            if(seele$transparentSections[sectionIndex]==0)
                seele$transparentSections[sectionIndex]=(byte)(section.maybeHas(s->!SkySourceScanR24.transparent(s))?2:1);
            if(seele$transparentSections[sectionIndex]==1)
            {
                // The edge from a potentially shaped preceding block must
                // still be checked. All interior edges here are empty.
                if(!previousClear&&isEdgeOccluded(chunk,above.set(x,base+16,z),previous,below.set(x,base+15,z),Blocks.AIR.defaultBlockState()))
                {callback.setReturnValue(base+16);return;}
                previous=Blocks.AIR.defaultBlockState();previousClear=true;continue;
            }
            for(int localY=15;localY>=0;localY--)
            {
                BlockState current=section.getBlockState(x,localY,z);boolean clear=SkySourceScanR24.transparent(current);int y=base+localY;
                // Positions retain vanilla's local X/Z convention for a
                // ChunkAccess. Unknown and dynamic states use its exact test.
                if((!previousClear||!clear)&&isEdgeOccluded(chunk,above.set(x,y+1,z),previous,below.set(x,y,z),current))
                {callback.setReturnValue(y+1);return;}
                previous=current;previousClear=clear;
            }
        }
        callback.setReturnValue(minY);
    }
}
