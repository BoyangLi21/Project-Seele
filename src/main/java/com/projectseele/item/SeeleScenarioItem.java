package com.projectseele.item;

import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.network.ClientboundThirdImpactPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModEntities;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraftforge.network.PacketDistributor;

/** Creative story tool: manifests the Tree of Life and deploys the nine white EVAs. */
public class SeeleScenarioItem extends Item
{
    public SeeleScenarioItem(Properties properties)
    {
        super(properties);
    }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand)
    {
        ItemStack stack = player.getItemInHand(hand);
        if (!(level instanceof ServerLevel server) || !(player instanceof ServerPlayer serverPlayer))
        {
            return InteractionResultHolder.sidedSuccess(stack, level.isClientSide);
        }
        double centerX = player.getX();
        double centerY = player.getY();
        double centerZ = player.getZ();
        for (int i = 0; i < 9; i++)
        {
            double angle = Math.PI * 2.0D * i / 9.0D;
            MassProductionEvaEntity mass = ModEntities.MASS_PRODUCTION_EVA.get().create(server);
            if (mass != null)
            {
                mass.moveTo(centerX + Math.cos(angle) * 38.0D,
                        centerY + 22.0D + (i % 3) * 5.0D,
                        centerZ + Math.sin(angle) * 38.0D,
                        (float) Math.toDegrees(-angle), 0.0F);
                server.addFreshEntity(mass);
            }
        }
        SeeleNetwork.CHANNEL.send(PacketDistributor.ALL.noArg(),
                new ClientboundThirdImpactPacket(centerX, centerY + 12.0D, centerZ));
        serverPlayer.getCooldowns().addCooldown(this, 20 * 30);
        serverPlayer.displayClientMessage(Component.translatable("message.projectseele.scenario_started"), false);
        return InteractionResultHolder.success(stack);
    }
}
