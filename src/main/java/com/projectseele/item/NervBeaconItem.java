package com.projectseele.item;

import com.projectseele.event.AngelSiegeDirector;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.Blocks;

/** Places the defended NERV target and starts a three-Angel siege. */
public class NervBeaconItem extends Item
{
    public NervBeaconItem(Properties properties)
    {
        super(properties);
    }

    @Override
    public InteractionResult useOn(UseOnContext context)
    {
        if (!(context.getLevel() instanceof ServerLevel level)
                || !(context.getPlayer() instanceof ServerPlayer player))
        {
            return InteractionResult.SUCCESS;
        }
        BlockPos base = context.getClickedPos().above();
        if (AngelSiegeDirector.hasActiveNear(level, base))
        {
            player.displayClientMessage(Component.translatable("message.projectseele.siege_already_active"), false);
            return InteractionResult.FAIL;
        }
        for (int x = -1; x <= 1; x++)
        {
            for (int z = -1; z <= 1; z++)
            {
                level.setBlock(base.offset(x, 0, z), Blocks.IRON_BLOCK.defaultBlockState(), 3);
            }
        }
        BlockPos beacon = base.above();
        level.setBlock(beacon, Blocks.LODESTONE.defaultBlockState(), 3);
        level.setBlock(beacon.above(), Blocks.LIGHTNING_ROD.defaultBlockState(), 3);
        AngelSiegeDirector.start(level, beacon, player);
        player.getCooldowns().addCooldown(this, 20 * 60);
        return InteractionResult.CONSUME;
    }
}
