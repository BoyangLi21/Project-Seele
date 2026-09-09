package com.projectseele.world;

import com.projectseele.registry.ModBlockEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/** Non-ticking facade pane; all optical state comes from the block state. */
public final class OneWayGlassBlockEntity extends BlockEntity
{
    public OneWayGlassBlockEntity(BlockPos position,BlockState state)
    {
        super(ModBlockEntities.ONE_WAY_GLASS.get(),position,state);
    }
}
