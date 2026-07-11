package com.projectseele.item;

import com.projectseele.entity.EvaUnit01Entity;
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
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.ProjectileUtil;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.network.PacketDistributor;

/**
 * Creative story tool. Aimed at an EVA Unit, it hoists that Unit into the
 * sky and nails it to Tiferet — arms out, gravity off, pilot and all — then
 * manifests the blood-red Tree of Life around it with one Mass-Production
 * Eva hovering on each outer Sephira. Used again on a crucified Unit, it
 * releases it (with slow falling). Aimed at nothing, it stages the tree
 * ahead of the viewer with a light-silhouette at the centre instead.
 */
public class SeeleScenarioItem extends Item
{
    private static final double AIM_RANGE = 160.0D;
    private static final double TREE_DISTANCE = 260.0D;
    private static final double TREE_BASE_HEIGHT = 100.0D;

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

        EvaUnit01Entity aimedUnit = findAimedUnit(server, serverPlayer);
        if (aimedUnit != null && aimedUnit.isCrucified())
        {
            // Second use: take it down from the Tree.
            aimedUnit.setCrucified(false);
            aimedUnit.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, 20 * 60, 0));
            serverPlayer.displayClientMessage(
                    Component.translatable("message.projectseele.scenario_released"), false);
            return InteractionResultHolder.success(stack);
        }

        Vec3 origin;
        float yaw;
        boolean hasUnit = aimedUnit != null;
        if (hasUnit)
        {
            // The Tree sprouts around the chosen Unit: Tiferet directly above
            // where it stands now.
            Vec3 base = aimedUnit.position();
            origin = new Vec3(base.x, base.y + TREE_BASE_HEIGHT, base.z);
            Vec3 toViewer = serverPlayer.position().subtract(origin).multiply(1.0D, 0.0D, 1.0D);
            yaw = (float) Mth.atan2(toViewer.x, toViewer.z);
            Vec3 tiferet = TreeOfLifeLayout.worldNode(origin, yaw, TreeOfLifeLayout.TIFERET);
            aimedUnit.teleportTo(tiferet.x, tiferet.y - aimedUnit.getBbHeight() * 0.5D, tiferet.z);
            aimedUnit.setYRot((float) Math.toDegrees(yaw) + 180.0F);
            aimedUnit.setCrucified(true);
        }
        else
        {
            Vec3 look = player.getLookAngle().multiply(1.0D, 0.0D, 1.0D);
            if (look.lengthSqr() < 1.0E-4D)
            {
                look = new Vec3(0.0D, 0.0D, 1.0D);
            }
            look = look.normalize();
            origin = player.position().add(look.scale(TREE_DISTANCE)).add(0.0D, TREE_BASE_HEIGHT, 0.0D);
            Vec3 toViewer = player.position().subtract(origin);
            yaw = (float) Mth.atan2(toViewer.x, toViewer.z);
        }

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
            mass.moveTo(node.x, node.y - mass.getBbHeight() * 0.5D, node.z,
                    (float) Math.toDegrees(yaw) + 180.0F, 0.0F);
            mass.setNoGravity(true);
            mass.setNoAi(true);
            mass.setPersistenceRequired();
            server.addFreshEntity(mass);
        }

        SeeleNetwork.CHANNEL.send(PacketDistributor.ALL.noArg(),
                new ClientboundThirdImpactPacket(origin.x, origin.y, origin.z, yaw, hasUnit));
        serverPlayer.getCooldowns().addCooldown(this, 20 * 30);
        serverPlayer.displayClientMessage(Component.translatable("message.projectseele.scenario_started"), false);
        return InteractionResultHolder.success(stack);
    }

    private static EvaUnit01Entity findAimedUnit(ServerLevel server, ServerPlayer player)
    {
        Vec3 from = player.getEyePosition();
        Vec3 to = from.add(player.getLookAngle().scale(AIM_RANGE));
        EntityHitResult hit = ProjectileUtil.getEntityHitResult(server, player, from, to,
                new AABB(from, to).inflate(2.0D),
                e -> e instanceof EvaUnit01Entity && e.isAlive());
        if (hit != null && hit.getEntity() instanceof EvaUnit01Entity unit)
        {
            return unit;
        }
        // Also accept the Unit the player is currently piloting.
        if (player.getVehicle() instanceof EvaUnit01Entity ridden)
        {
            return ridden;
        }
        return null;
    }
}
