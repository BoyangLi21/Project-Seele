package com.projectseele.world;

import java.util.Comparator;

import javax.annotation.Nullable;

import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
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
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Interactive NERV rack which physically exchanges one armament with an EVA. */
public final class EvaArmamentRackBlock extends BaseEntityBlock
{
    private static final int EVA_SEARCH_RANGE = 48;
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

        EvaUnit01Entity eva = findNearestEva(serverLevel, pos);
        if (player.isSecondaryUseActive())
        {
            if (eva != null && eva.getWeapon() != EvaUnit01Entity.WEAPON_FISTS)
            {
                ItemStack returned = EvaArmamentRackBlockEntity.stackForWeapon(
                        eva.getWeapon());
                if (returned.isEmpty() || !rack.insertOne(returned))
                {
                    player.displayClientMessage(Component.translatable(
                            "msg.projectseele.armament_rack_full"), true);
                    return InteractionResult.FAIL;
                }
                eva.unloadRackArmament();
                player.displayClientMessage(Component.translatable(
                        "msg.projectseele.armament_rack_unloaded"), true);
                serverLevel.playSound(null, pos, SoundEvents.IRON_TRAPDOOR_CLOSE,
                        SoundSource.BLOCKS, 0.9F, 0.8F);
                return InteractionResult.CONSUME;
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

        if (eva == null)
        {
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_no_eva", EVA_SEARCH_RANGE), true);
            return InteractionResult.FAIL;
        }
        if (!eva.canReceiveRackArmament())
        {
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_busy"), true);
            return InteractionResult.FAIL;
        }

        ItemStack selected = rack.takeNextArmament();
        if (selected.isEmpty())
        {
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_empty"), true);
            return InteractionResult.FAIL;
        }
        int weapon = EvaArmamentRackBlockEntity.weaponFor(selected);
        ItemStack previous = EvaArmamentRackBlockEntity.stackForWeapon(eva.getWeapon());
        if (!previous.isEmpty() && !rack.insertOne(previous))
        {
            rack.insertOne(selected);
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_full"), true);
            return InteractionResult.FAIL;
        }
        if (!eva.equipRackArmament(weapon))
        {
            if (!previous.isEmpty())
            {
                rack.removeOneWeapon(eva.getWeapon());
            }
            rack.insertOne(selected);
            player.displayClientMessage(Component.translatable(
                    "msg.projectseele.armament_rack_busy"), true);
            return InteractionResult.FAIL;
        }

        player.displayClientMessage(Component.translatable(
                "msg.projectseele.armament_rack_equipped",
                Component.translatable(eva.getWeaponTranslationKey())), true);
        serverLevel.playSound(null, pos, SoundEvents.DISPENSER_DISPENSE,
                SoundSource.BLOCKS, 1.0F, 0.65F);
        return InteractionResult.CONSUME;
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

    @Nullable
    private static EvaUnit01Entity findNearestEva(ServerLevel level, BlockPos pos)
    {
        Vec3 centre = Vec3.atCenterOf(pos);
        AABB bounds = new AABB(pos).inflate(EVA_SEARCH_RANGE,
                EVA_SEARCH_RANGE, EVA_SEARCH_RANGE);
        return level.getEntitiesOfClass(EvaUnit01Entity.class, bounds,
                        eva -> eva.isAlive() && !eva.isRemoved())
                .stream()
                .min(Comparator.comparingDouble(eva ->
                        eva.distanceToSqr(centre)))
                .orElse(null);
    }
}