package com.projectseele.world;

import javax.annotation.Nullable;

import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Interactive NERV rack which physically exchanges one armament with an EVA. */
public final class EvaArmamentRackBlock extends BaseEntityBlock
{
    private static final VoxelShape SHAPE = box(1.0D, 0.0D, 2.0D,
            15.0D, 16.0D, 16.0D);

    public EvaArmamentRackBlock(Properties properties)
    {
        super(properties);
    }

    @Nullable
    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state)
    {
        return new EvaArmamentRackBlockEntity(pos, state);
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

    @Override
    public InteractionResult use(BlockState state, Level level, BlockPos pos,
                                 Player player, InteractionHand hand,
                                 BlockHitResult hit)
    {
        if (hand != InteractionHand.MAIN_HAND)
        {
            return InteractionResult.PASS;
        }
        if (!(level instanceof ServerLevel serverLevel))
        {
            return InteractionResult.SUCCESS;
        }
        if (!(player instanceof ServerPlayer serverPlayer))
        {
            return InteractionResult.FAIL;
        }
        if (!(level.getBlockEntity(pos) instanceof EvaArmamentRackBlockEntity rack))
        {
            return InteractionResult.FAIL;
        }

        ItemStack held = player.getItemInHand(hand);
        if (!held.isEmpty() && EvaArmamentRackBlockEntity.weaponFor(held) >= 0)
        {
            if (!rack.insertOne(held))
            {
                player.displayClientMessage(Component.translatable(
                        "msg.projectseele.armament_rack_full"), true);
                return InteractionResult.FAIL;
            }
            Component name = held.getHoverName();
            if (!player.getAbilities().instabuild)
            {
                held.shrink(1);
            }
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_loaded", name), true);
            serverLevel.playSound(null, pos, SoundEvents.IRON_DOOR_CLOSE,
                    SoundSource.BLOCKS, 0.8F, 1.25F);
            return InteractionResult.CONSUME;
        }
        if (!held.isEmpty())
        {
            return InteractionResult.PASS;
        }

        if (player.isSecondaryUseActive())
        {
            if (EvaWeaponLiftDirector.requestReturn(serverPlayer, pos))
            {
                return InteractionResult.CONSUME;
            }
            if (EvaWeaponLiftDirector.hasActiveSequence(serverLevel, pos))
            {
                return InteractionResult.FAIL;
            }

            ItemStack retrieved = rack.takeNextArmament();
            if (retrieved.isEmpty())
            {
                player.displayClientMessage(Component.translatable(
                        "msg.projectseele.armament_rack_empty"), true);
                return InteractionResult.FAIL;
            }
            Component name = retrieved.getHoverName();
            if (!player.getInventory().add(retrieved))
            {
                player.drop(retrieved, false);
            }
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_retrieved", name), true);
            serverLevel.playSound(null, pos, SoundEvents.ITEM_PICKUP,
                    SoundSource.BLOCKS, 0.8F, 0.75F);
            return InteractionResult.CONSUME;
        }

        return EvaWeaponLiftDirector.requestPresentation(serverPlayer, pos, rack)
                ? InteractionResult.CONSUME : InteractionResult.FAIL;
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos,
                         BlockState newState, boolean moving)
    {
        if (!state.is(newState.getBlock())
                && level.getBlockEntity(pos) instanceof EvaArmamentRackBlockEntity rack)
        {
            Containers.dropContents(level, pos, rack);
            level.updateNeighbourForOutputSignal(pos, this);
        }
        super.onRemove(state, level, pos, newState, moving);
    }

}
