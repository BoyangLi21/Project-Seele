package com.projectseele.item;

import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.fx.TreeOfLifeLayout;
import com.projectseele.network.ClientboundThirdImpactPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModEntities;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;

/**
 * Creative story tool: manifests the Tree of Life in front of the user and
 * parks one white Mass-Production Eva on each of the nine outer Sephirot
 * (Tiferet belongs to the crucified Unit-01, drawn by the sky effect). The
 * server entities and the client light share {@link TreeOfLifeLayout}, so
 * the Evas hang exactly inside their rings.
 */
public class SeeleScenarioItem extends Item
{
    private static final double TREE_DISTANCE = 70.0D;
    private static final double TREE_BASE_HEIGHT = 14.0D;

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
        // Plant the tree ahead of the viewer so the whole diagram is on screen.
        Vec3 look = player.getLookAngle().multiply(1.0D, 0.0D, 1.0D);
        if (look.lengthSqr() < 1.0E-4D)
        {
            look = new Vec3(0.0D, 0.0D, 1.0D);
        }
        look = look.normalize();
        Vec3 origin = player.position().add(look.scale(TREE_DISTANCE)).add(0.0D, TREE_BASE_HEIGHT, 0.0D);
        // The tree plane faces back toward the viewer.
        Vec3 toViewer = player.position().subtract(origin);
        float yaw = (float) Mth.atan2(toViewer.x, toViewer.z);

        for (int i = 0; i < TreeOfLifeLayout.NODES.length; i++)
        {
            if (i == TreeOfLifeLayout.TIFERET)
            {
                continue; // the centre belongs to Unit-01
            }
            MassProductionEvaEntity mass = ModEntities.MASS_PRODUCTION_EVA.get().create(server);
            if (mass == null)
            {
                continue;
            }
            Vec3 node = TreeOfLifeLayout.worldNode(origin, yaw, i);
            // Face the audience along the tree plane's outward normal.
            float facing = (float) Math.toDegrees(Math.atan2(-toViewer.x, toViewer.z)) + 180.0F;
            mass.moveTo(node.x, node.y - mass.getBbHeight() * 0.5D, node.z, facing, 0.0F);
            mass.setNoGravity(true);
            mass.setNoAi(true);
            mass.setPersistenceRequired();
            server.addFreshEntity(mass);
        }

        SeeleNetwork.CHANNEL.send(PacketDistributor.ALL.noArg(),
                new ClientboundThirdImpactPacket(origin.x, origin.y, origin.z, yaw));
        serverPlayer.getCooldowns().addCooldown(this, 20 * 30);
        serverPlayer.displayClientMessage(Component.translatable("message.projectseele.scenario_started"), false);
        return InteractionResultHolder.success(stack);
    }
}
