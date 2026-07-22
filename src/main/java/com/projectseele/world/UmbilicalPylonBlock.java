package com.projectseele.world;

import javax.annotation.Nullable;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Industrial external-power socket used by active EVA units. */
public final class UmbilicalPylonBlock extends BaseEntityBlock
{
    private static final VoxelShape SHAPE = box(2.0D, 0.0D, 2.0D,
            14.0D, 16.0D, 14.0D);

    public UmbilicalPylonBlock(Properties properties)
    {
        super(properties);
    }

    @Nullable
    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state)
    {
        return new UmbilicalPylonBlockEntity(pos, state);
    }

    @Override
    public RenderShape getRenderShape(BlockState state)
    {
        return RenderShape.MODEL;
    }

    @Override
    public VoxelShape getShape(BlockState state, BlockGetter level,
                               BlockPos pos, CollisionContext context)
    {
        return SHAPE;
    }
}