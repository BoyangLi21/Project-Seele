package com.projectseele.mixin;

import com.projectseele.world.CollisionChunkRevisionR24;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.*;

@Mixin(LevelChunk.class)
public abstract class CollisionChunkRevisionR24Mixin implements CollisionChunkRevisionR24
{
    @Unique private long seele$collisionVersion;
    @Override public long seele$collisionRevision(){return seele$collisionVersion;}
    @Inject(method="setBlockState",at=@At("RETURN"))
    private void seele$blockChanged(CallbackInfoReturnable<BlockState> result)
    {if(result.getReturnValue()!=null)seele$collisionVersion++;}
    @Inject(method="replaceWithPacketData",at=@At("HEAD"))
    private void seele$packetChanged(CallbackInfo callback){seele$collisionVersion++;}
}
