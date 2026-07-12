package com.projectseele.event;

import java.util.ArrayList;
import java.util.Collections;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import com.projectseele.ProjectSeele;
import com.projectseele.entity.MassProductionEvaEntity;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.fx.CrossExplosionFX;
import com.projectseele.fx.TreeOfLifeLayout;
import com.projectseele.network.ClientboundNukeFxPacket;
import com.projectseele.network.ClientboundThirdImpactPacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModEntities;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;
import org.jetbrains.annotations.Nullable;

/** Server-authoritative timeline for the Third Impact tableau. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ThirdImpactDirector
{
    private static final int TREE_MANIFEST_TICK = 300;
    private static final int TIMELINE_FINISH_TICK = 1200;
    /** Client KabbalahTree lifetime begins when the Tree manifests. */
    private static final int TREE_EFFECT_TICKS = 20 * 180;
    private static final int PERSIST_UNTIL_TICK = TREE_MANIFEST_TICK + TREE_EFFECT_TICKS;
    private static final List<Impact> ACTIVE = new ArrayList<>();
    private static final Set<ServerLevel> RESTORED_LEVELS =
            Collections.newSetFromMap(new IdentityHashMap<>());

    private ThirdImpactDirector() {}

    public static void start(ServerLevel level, Vec3 origin, float yaw, boolean hasUnit)
    {
        ensureRestored(level);
        Impact impact = new Impact(level, origin, yaw, hasUnit, true);
        ACTIVE.add(impact);
        persist(impact);
        ProjectSeele.LOGGER.info(
                "Third Impact staged: dimension={} origin=({},{},{}) yaw={} unit01={}",
                level.dimension().location(), origin.x, origin.y, origin.z, yaw, hasUnit);
        broadcast(impact, "message.projectseele.impact_ascent");
    }

    /** Development visual-lab entry: materialise the complete tableau now. */
    public static void startVisualPreview(ServerLevel level, Vec3 origin, float yaw, boolean hasUnit)
    {
        ACTIVE.removeIf(existing -> !existing.persistent && existing.level == level
                && existing.origin.distanceToSqr(origin) < 32.0D * 32.0D);
        Impact impact = new Impact(level, origin, yaw, hasUnit, false);
        impact.ticks = 300;
        deployVessels(impact);
        auditTableau(impact, "visual-preview");
        ACTIVE.add(impact);
        sendTreeToDimension(impact);
        broadcast(impact, "message.projectseele.impact_tree");
    }

    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event)
    {
        if (event.phase != TickEvent.Phase.END)
        {
            return;
        }
        for (ServerLevel level : event.getServer().getAllLevels())
        {
            ensureRestored(level);
        }
        if (ACTIVE.isEmpty())
        {
            return;
        }
        Iterator<Impact> iterator = ACTIVE.iterator();
        while (iterator.hasNext())
        {
            Impact impact = iterator.next();
            if (impact.restoreDelay >= 0)
            {
                if (impact.ticks < TIMELINE_FINISH_TICK && !formationChunksLoaded(impact))
                {
                    continue;
                }
                if (impact.restoreDelay-- > 0)
                {
                    continue;
                }
                if (impact.ticks < TIMELINE_FINISH_TICK)
                {
                    reconcileRestoredImpact(impact);
                }
                impact.restoreDelay = -1;
                if (impact.ticks >= TREE_MANIFEST_TICK
                        && impact.ticks < PERSIST_UNTIL_TICK)
                {
                    sendTreeToDimension(impact);
                }
            }
            impact.ticks++;
            if (impact.ticks == 100)
            {
                deployVessels(impact);
                broadcast(impact, "message.projectseele.impact_formation");
            }
            else if (impact.ticks == TREE_MANIFEST_TICK)
            {
                auditTableau(impact, "tree-manifest");
                sendTreeToDimension(impact);
                broadcast(impact, "message.projectseele.impact_tree");
            }
            else if (impact.ticks == 560)
            {
                Vec3 centre = TreeOfLifeLayout.worldNode(impact.origin, impact.yaw, TreeOfLifeLayout.TIFERET);
                SeeleNetwork.CHANNEL.send(PacketDistributor.DIMENSION.with(impact.level::dimension),
                        new ClientboundNukeFxPacket(centre.x, centre.y, centre.z, 3.6F, false));
                CrossExplosionFX.spawn(impact.level, centre, 1.6F);
                broadcast(impact, "message.projectseele.impact_threshold");
            }
            else if (impact.ticks == 760)
            {
                applyLclPhase(impact);
                broadcast(impact, "message.projectseele.impact_instrumentality");
            }
            else if (impact.ticks == TIMELINE_FINISH_TICK)
            {
                finish(impact);
            }
            else if (impact.ticks >= PERSIST_UNTIL_TICK)
            {
                removePersisted(impact);
                iterator.remove();
                continue;
            }
            persist(impact);
        }
    }

    @SubscribeEvent
    public static void onLevelUnload(LevelEvent.Unload event)
    {
        if (event.getLevel() instanceof ServerLevel level)
        {
            ACTIVE.removeIf(impact -> impact.level == level);
            RESTORED_LEVELS.remove(level);
        }
    }

    @SubscribeEvent
    public static void onServerStopped(ServerStoppedEvent event)
    {
        ACTIVE.clear();
        RESTORED_LEVELS.clear();
    }

    private static void deployVessels(Impact impact)
    {
        float formationYaw = TreeOfLifeLayout.frontFacingYawDegrees(impact.yaw);
        int deployed = 0;
        for (int i = 0; i < TreeOfLifeLayout.NODES.length; i++)
        {
            if (i == TreeOfLifeLayout.TIFERET)
            {
                continue;
            }
            MassProductionEvaEntity mass = createVessel(impact, i, formationYaw);
            if (mass != null)
            {
                deployed++;
            }
        }
        ProjectSeele.LOGGER.info(
                "Third Impact formation deployed: vessels={} expected=9 frontYaw={}",
                deployed, formationYaw);
        if (deployed != TreeOfLifeLayout.NODES.length - 1)
        {
            ProjectSeele.LOGGER.error(
                    "THIRD IMPACT FORMATION INVALID: deployed {} of 9 Mass Production EVAs",
                    deployed);
        }
        persist(impact);
    }

    @Nullable
    private static MassProductionEvaEntity createVessel(Impact impact, int nodeIndex,
                                                        float formationYaw)
    {
        MassProductionEvaEntity mass = ModEntities.MASS_PRODUCTION_EVA.get().create(impact.level);
        if (mass == null)
        {
            return null;
        }
        configureVessel(impact, nodeIndex, formationYaw, mass);
        if (!impact.level.addFreshEntity(mass))
        {
            return null;
        }
        impact.vesselIds.put(nodeIndex, mass.getUUID());
        return mass;
    }

    private static void configureVessel(Impact impact, int nodeIndex, float formationYaw,
                                        MassProductionEvaEntity mass)
    {
        Vec3 node = TreeOfLifeLayout.worldNode(impact.origin, impact.yaw, nodeIndex);
        mass.moveTo(node.x, node.y - mass.getBbHeight() * 0.5D, node.z, formationYaw, 0.0F);
        faceFront(mass, formationYaw);
        mass.setDeltaMovement(Vec3.ZERO);
        mass.setNoGravity(true);
        mass.setNoAi(true);
        mass.setVisualPose(MassProductionEvaEntity.VISUAL_RITUAL);
        mass.setPersistenceRequired();
    }

    private static void ensureRestored(ServerLevel level)
    {
        if (!RESTORED_LEVELS.add(level))
        {
            return;
        }
        int restored = 0;
        for (ThirdImpactSavedData.StoredImpact stored : ThirdImpactSavedData.get(level).impacts())
        {
            boolean alreadyActive = ACTIVE.stream().anyMatch(impact -> impact.level == level
                    && impact.id.equals(stored.id()));
            if (!alreadyActive)
            {
                ACTIVE.add(new Impact(level, stored));
                restored++;
            }
        }
        if (restored > 0)
        {
            ProjectSeele.LOGGER.info("Third Impact restored: dimension={} timelines={}",
                    level.dimension().location(), restored);
        }
    }

    private static boolean formationChunksLoaded(Impact impact)
    {
        for (int node = 0; node < TreeOfLifeLayout.NODES.length; node++)
        {
            Vec3 position = TreeOfLifeLayout.worldNode(impact.origin, impact.yaw, node);
            if (!impact.level.hasChunkAt(BlockPos.containing(position)))
            {
                return false;
            }
        }
        return true;
    }

    private static void reconcileRestoredImpact(Impact impact)
    {
        if (impact.ticks < 100)
        {
            persist(impact);
            return;
        }
        impact.vesselIds.remove(TreeOfLifeLayout.TIFERET);
        float formationYaw = TreeOfLifeLayout.frontFacingYawDegrees(impact.yaw);
        int recovered = 0;
        int replaced = 0;
        for (int node = 0; node < TreeOfLifeLayout.NODES.length; node++)
        {
            if (node == TreeOfLifeLayout.TIFERET)
            {
                continue;
            }
            UUID vesselId = impact.vesselIds.get(node);
            net.minecraft.world.entity.Entity entity = vesselId == null
                    ? null : impact.level.getEntity(vesselId);
            if (entity instanceof MassProductionEvaEntity mass && mass.isAlive())
            {
                configureVessel(impact, node, formationYaw, mass);
                recovered++;
                continue;
            }
            impact.vesselIds.remove(node);
            if (createVessel(impact, node, formationYaw) != null)
            {
                replaced++;
            }
        }
        persist(impact);
        ProjectSeele.LOGGER.info(
                "Third Impact vessel reconciliation: event={} recovered={} replaced={} total={}",
                impact.id, recovered, replaced, impact.vesselIds.size());
        if (impact.vesselIds.size() != 9)
        {
            ProjectSeele.LOGGER.error(
                    "THIRD IMPACT RESTORE INVALID: event={} restored {} of 9 vessels",
                    impact.id, impact.vesselIds.size());
        }
    }

    private static void persist(Impact impact)
    {
        if (!impact.persistent)
        {
            return;
        }
        ThirdImpactSavedData.get(impact.level).put(new ThirdImpactSavedData.StoredImpact(
                impact.id, impact.origin, impact.yaw, impact.hasUnit, impact.ticks,
                impact.vesselIds));
    }

    private static void removePersisted(Impact impact)
    {
        if (impact.persistent)
        {
            ThirdImpactSavedData.get(impact.level).remove(impact.id);
        }
    }

    private static ClientboundThirdImpactPacket treePacket(Impact impact)
    {
        return new ClientboundThirdImpactPacket(impact.origin.x, impact.origin.y,
                impact.origin.z, impact.yaw, impact.hasUnit,
                Math.max(0, impact.ticks - TREE_MANIFEST_TICK));
    }

    private static void sendTreeToDimension(Impact impact)
    {
        SeeleNetwork.CHANNEL.send(PacketDistributor.DIMENSION.with(impact.level::dimension),
                treePacket(impact));
    }

    /** Rebuild the client-side Tree after login, respawn or dimension change. */
    public static void syncTo(ServerPlayer player)
    {
        ServerLevel level = player.serverLevel();
        ensureRestored(level);
        for (Impact impact : ACTIVE)
        {
            if (impact.level == level && impact.ticks >= TREE_MANIFEST_TICK
                    && impact.ticks < PERSIST_UNTIL_TICK)
            {
                SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                        treePacket(impact));
            }
        }
    }

    /**
     * Server-side structural gate for both the story timeline and Visual Lab.
     * This deliberately checks state and placement only; it never claims that
     * the resulting composition or animation has passed visual review.
     */
    private static void auditTableau(Impact impact, String stage)
    {
        AABB area = new AABB(impact.origin, impact.origin).inflate(230.0D);
        List<MassProductionEvaEntity> vessels = impact.level.getEntitiesOfClass(
                MassProductionEvaEntity.class, area,
                mass -> mass.isAlive() && impact.vesselIds.containsValue(mass.getUUID()));
        float expectedYaw = TreeOfLifeLayout.frontFacingYawDegrees(impact.yaw);
        int facing = 0;
        int ritual = 0;
        boolean[] occupied = new boolean[TreeOfLifeLayout.NODES.length];
        for (MassProductionEvaEntity mass : vessels)
        {
            if (mass.isRitualFormation())
            {
                ritual++;
            }
            boolean front = Math.abs(net.minecraft.util.Mth.wrapDegrees(
                    mass.getYRot() - expectedYaw)) < 1.0F
                    && Math.abs(net.minecraft.util.Mth.wrapDegrees(
                            mass.yBodyRot - expectedYaw)) < 1.0F
                    && Math.abs(net.minecraft.util.Mth.wrapDegrees(
                            mass.yHeadRot - expectedYaw)) < 1.0F;
            if (front)
            {
                facing++;
            }
            Vec3 centre = mass.position().add(0.0D, mass.getBbHeight() * 0.5D, 0.0D);
            for (int node = 0; node < TreeOfLifeLayout.NODES.length; node++)
            {
                if (node == TreeOfLifeLayout.TIFERET)
                {
                    continue;
                }
                if (centre.distanceToSqr(TreeOfLifeLayout.worldNode(
                        impact.origin, impact.yaw, node)) < 1.0D)
                {
                    occupied[node] = true;
                    break;
                }
            }
        }
        int occupiedOuterNodes = 0;
        for (int node = 0; node < occupied.length; node++)
        {
            if (node != TreeOfLifeLayout.TIFERET && occupied[node])
            {
                occupiedOuterNodes++;
            }
        }

        Vec3 tiferet = TreeOfLifeLayout.worldNode(
                impact.origin, impact.yaw, TreeOfLifeLayout.TIFERET);
        boolean crucifiedUnit01 = !impact.hasUnit;
        boolean unitAtTiferet = !impact.hasUnit;
        boolean unitFacingFront = !impact.hasUnit;
        boolean alignedCrucifiedUnit01 = !impact.hasUnit;
        if (impact.hasUnit)
        {
            for (EvaUnit01Entity unit : impact.level.getEntitiesOfClass(
                    EvaUnit01Entity.class, area,
                    unit -> unit.isAlive()
                            && unit.getUnitVariant() == EvaUnit01Entity.UNIT_01
                            && unit.isCrucified()))
            {
                crucifiedUnit01 = true;
                Vec3 centre = unit.position().add(0.0D, unit.getBbHeight() * 0.5D, 0.0D);
                boolean atTiferet = centre.distanceToSqr(tiferet) < 1.0D;
                boolean facingFront = Math.abs(net.minecraft.util.Mth.wrapDegrees(
                        unit.getYRot() - expectedYaw)) < 1.0F;
                unitAtTiferet |= atTiferet;
                unitFacingFront |= facingFront;
                alignedCrucifiedUnit01 |= atTiferet && facingFront;
            }
        }

        boolean valid = vessels.size() == 9 && facing == 9 && ritual == 9
                && occupiedOuterNodes == 9
                && crucifiedUnit01 && alignedCrucifiedUnit01;
        ProjectSeele.LOGGER.info(
                "Third Impact tableau audit [{}]: valid={} vessels={} facingFront={} ritual={} occupiedOuterNodes={} crucifiedUnit01={} unitAtTiferet={} unitFacingFront={} alignedUnit01={}",
                stage, valid, vessels.size(), facing, ritual, occupiedOuterNodes, crucifiedUnit01,
                unitAtTiferet, unitFacingFront, alignedCrucifiedUnit01);
        if (!valid)
        {
            ProjectSeele.LOGGER.error(
                    "THIRD IMPACT TABLEAU INVALID [{}]: structural state failed; visual acceptance remains separate",
                    stage);
        }
    }

    /** Keep every ritual vessel on one readable front plane. */
    private static void faceFront(net.minecraft.world.entity.LivingEntity entity, float yaw)
    {
        entity.setYRot(yaw);
        entity.setXRot(0.0F);
        entity.yRotO = yaw;
        entity.xRotO = 0.0F;
        entity.yBodyRot = yaw;
        entity.yBodyRotO = yaw;
        entity.yHeadRot = yaw;
        entity.yHeadRotO = yaw;
    }

    private static void applyLclPhase(Impact impact)
    {
        AABB area = new AABB(impact.origin, impact.origin).inflate(220.0D);
        for (ServerPlayer player : impact.level.getEntitiesOfClass(ServerPlayer.class, area))
        {
            player.addEffect(new MobEffectInstance(MobEffects.SLOW_FALLING, 20 * 45, 0));
            player.addEffect(new MobEffectInstance(MobEffects.ABSORPTION, 20 * 45, 3));
            player.addEffect(new MobEffectInstance(MobEffects.GLOWING, 20 * 45, 0));
        }
    }

    private static void finish(Impact impact)
    {
        if (!impact.hasUnit)
        {
            broadcast(impact, "message.projectseele.impact_complete");
            return;
        }
        AABB area = new AABB(impact.origin, impact.origin).inflate(240.0D);
        Vec3 tiferet = TreeOfLifeLayout.worldNode(
                impact.origin, impact.yaw, TreeOfLifeLayout.TIFERET);
        float expectedYaw = TreeOfLifeLayout.frontFacingYawDegrees(impact.yaw);
        boolean accepted = impact.level.getEntitiesOfClass(EvaUnit01Entity.class, area,
                unit -> unit.isAlive()
                        && unit.getUnitVariant() == EvaUnit01Entity.UNIT_01
                        && unit.isCrucified()
                        && unit.position().add(0.0D, unit.getBbHeight() * 0.5D, 0.0D)
                                .distanceToSqr(tiferet) < 1.0D
                        && Math.abs(net.minecraft.util.Mth.wrapDegrees(
                                unit.getYRot() - expectedYaw)) < 1.0F).stream().findAny().isPresent();
        if (accepted)
        {
            broadcast(impact, "message.projectseele.impact_accepted");
        }
        else
        {
            // Releasing the crucified Unit before the final phase rejects the
            // scenario; the nine inert vessels fall apart with the tableau.
            for (MassProductionEvaEntity mass :
                    impact.level.getEntitiesOfClass(MassProductionEvaEntity.class, area,
                            entity -> impact.vesselIds.containsValue(entity.getUUID())))
            {
                mass.discard();
            }
            broadcast(impact, "message.projectseele.impact_rejected");
        }
    }

    private static void broadcast(Impact impact, String key)
    {
        for (ServerPlayer player : impact.level.players())
        {
            if (player.position().distanceToSqr(impact.origin) < 420.0D * 420.0D)
            {
                player.displayClientMessage(Component.translatable(key), false);
            }
        }
    }

    private static final class Impact
    {
        final UUID id;
        final ServerLevel level;
        final Vec3 origin;
        final float yaw;
        final boolean hasUnit;
        final boolean persistent;
        final Map<Integer, UUID> vesselIds = new LinkedHashMap<>();
        int ticks;
        int restoreDelay = -1;

        Impact(ServerLevel level, Vec3 origin, float yaw, boolean hasUnit,
               boolean persistent)
        {
            this.id = UUID.randomUUID();
            this.level = level;
            this.origin = origin;
            this.yaw = yaw;
            this.hasUnit = hasUnit;
            this.persistent = persistent;
        }

        Impact(ServerLevel level, ThirdImpactSavedData.StoredImpact stored)
        {
            this.id = stored.id();
            this.level = level;
            this.origin = stored.origin();
            this.yaw = stored.yaw();
            this.hasUnit = stored.hasUnit();
            this.persistent = true;
            this.ticks = stored.ticks();
            this.vesselIds.putAll(stored.vessels());
            this.restoreDelay = stored.ticks() < TIMELINE_FINISH_TICK ? 20 : 0;
        }
    }
}
