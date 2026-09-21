package com.projectseele.item;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.*;
import net.minecraft.server.level.ServerPlayer;
public final class UNSatellitePhoneItem extends Item
{
    public UNSatellitePhoneItem(Properties properties){super(properties);}
    @Override public InteractionResultHolder<ItemStack> use(Level level,Player player,InteractionHand hand)
    {
        if(player instanceof ServerPlayer server)com.projectseele.world.UNCommandR29.receive(server,"open",0,0,0);
        return InteractionResultHolder.sidedSuccess(player.getItemInHand(hand),level.isClientSide);
    }
}
