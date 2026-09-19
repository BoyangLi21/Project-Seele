package com.projectseele.client;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.state.BlockState;
import java.util.IdentityHashMap;

/** Only proven, position-independent transparent states participate in section skipping. */
public final class SkySourceScanR24
{
    public static final ThreadLocal<Boolean> VANILLA=ThreadLocal.withInitial(()->false);
    private static final ThreadLocal<IdentityHashMap<BlockState,Boolean>> TRANSPARENT=ThreadLocal.withInitial(IdentityHashMap::new);
    private static final boolean DISABLED=Boolean.getBoolean("projectseele.vanillaSkyScan");
    public static boolean enabled(){return !DISABLED&&!VANILLA.get()&&com.mojang.blaze3d.systems.RenderSystem.isOnRenderThread();}
    public static boolean transparent(BlockState state)
    {
        if(state.is(Blocks.AIR)||state.is(Blocks.CAVE_AIR)||state.is(Blocks.VOID_AIR))return true;
        var cache=TRANSPARENT.get();Boolean known=cache.get(state);if(known!=null)return known;
        boolean clear=state.is(Blocks.LIGHT)&&state.getFluidState().isEmpty()
                ||state.getBlock().getClass()==GlassBlock.class&&!state.canOcclude()
                  &&state.getLightBlock(EmptyBlockGetter.INSTANCE,BlockPos.ZERO)==0;
        cache.put(state,clear);return clear;
    }
    private SkySourceScanR24(){}
}
