package com.projectseele.visual;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.suggestion.SuggestionProvider;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.network.ClientboundVisualCapturePacket;
import com.projectseele.network.SeeleNetwork;
import com.projectseele.registry.ModEntities;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;

/** Deterministic development arena and pose controls for visual regression. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class VisualLabCommands
{
    private static final String[] POSES = {
            "normal", "idle", "walk_contact", "crouch", "prone",
            "knife_windup", "knife_contact", "knife_recovery",
            "lance_windup", "lance_contact", "lance_recovery", "cannon"
    };
    private static final SuggestionProvider<CommandSourceStack> POSE_SUGGESTIONS =
            (context, builder) -> SharedSuggestionProvider.suggest(POSES, builder);

    private VisualLabCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("seele")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("visual")
                        .then(Commands.literal("setup").executes(context -> setup(context.getSource())))
                        .then(Commands.literal("spawn")
                                .then(Commands.literal("unit01")
                                        .executes(context -> spawn(context.getSource()))))
                        .then(Commands.literal("pose")
                                .then(Commands.argument("name", StringArgumentType.word())
                                        .suggests(POSE_SUGGESTIONS)
                                        .executes(context -> pose(context.getSource(),
                                                StringArgumentType.getString(context, "name")))))
                        .then(Commands.literal("capture")
                                .then(Commands.literal("all")
                                        .executes(context -> capture(context.getSource()))))));
    }

    static int setup(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        ServerLevel level = player.serverLevel();
        // This command is for the dedicated Visual Lab world. A fixed isolated
        // origin keeps captures independent from the player's previous
        // position, old high-altitude lab platforms, terrain and cloud height.
        BlockPos centre = new BlockPos(4096, 64, 4096);
        level.setDayTime(6000L);
        level.setWeatherParameters(6000, 0, false, false);

        for (int x = -45; x <= 45; x++)
        {
            for (int z = -45; z <= 45; z++)
            {
                boolean major = x % 10 == 0 || z % 10 == 0;
                level.setBlock(centre.offset(x, 0, z),
                        major ? Blocks.LIGHT_GRAY_CONCRETE.defaultBlockState()
                                : Blocks.GRAY_CONCRETE.defaultBlockState(), 3);
            }
        }
        // Height rulers: orange every five blocks, iron otherwise.
        for (int y = 1; y <= 30; y++)
        {
            level.setBlock(centre.offset(-32, y, -30),
                    y % 5 == 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                            : Blocks.IRON_BLOCK.defaultBlockState(), 3);
            level.setBlock(centre.offset(32, y, -30),
                    y % 5 == 0 ? Blocks.ORANGE_CONCRETE.defaultBlockState()
                            : Blocks.IRON_BLOCK.defaultBlockState(), 3);
        }
        // Door frame and step-height fixtures.
        for (int y = 1; y <= 22; y++)
        {
            level.setBlock(centre.offset(26, y, 18), Blocks.WHITE_CONCRETE.defaultBlockState(), 3);
            level.setBlock(centre.offset(26, y, 34), Blocks.WHITE_CONCRETE.defaultBlockState(), 3);
        }
        for (int z = -8; z <= 8; z++)
        {
            level.setBlock(centre.offset(26, 22, 26 + z), Blocks.WHITE_CONCRETE.defaultBlockState(), 3);
        }
        for (int step = 0; step < 5; step++)
        {
            for (int x = 0; x <= step; x++)
            {
                level.setBlock(centre.offset(-28 + x, 1 + step, 24),
                        Blocks.SMOOTH_STONE.defaultBlockState(), 3);
            }
        }
        level.setBlock(centre.above(), Blocks.LODESTONE.defaultBlockState(), 3);
        removeLabEntities(level, centre);
        EvaUnit01Entity unit = createUnit(level, centre.above());
        ArmorStand target = new ArmorStand(level, centre.getX() + 0.5D, centre.getY() + 1.0D,
                centre.getZ() + 28.5D);
        target.setNoGravity(true);
        target.setShowArms(true);
        target.setCustomName(Component.literal("VISUAL TARGET"));
        target.setCustomNameVisible(true);
        level.addFreshEntity(target);
        player.teleportTo(level, centre.getX() + 0.5D, centre.getY() + 2.0D,
                centre.getZ() + 42.5D, 180.0F, 5.0F);
        source.sendSuccess(() -> Component.literal("Visual Lab ready; Unit-01 id=" + unit.getId()), false);
        return 1;
    }

    private static int spawn(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        BlockPos centre = player.blockPosition();
        EvaUnit01Entity unit = createUnit(player.serverLevel(), centre);
        source.sendSuccess(() -> Component.literal("Visual Unit-01 spawned: " + unit.getId()), false);
        return 1;
    }

    private static EvaUnit01Entity createUnit(ServerLevel level, BlockPos position)
    {
        EvaUnit01Entity unit = ModEntities.EVA_UNIT01.get().create(level);
        if (unit == null)
        {
            throw new IllegalStateException("Unit-01 entity creation failed");
        }
        unit.moveTo(position.getX() + 0.5D, position.getY(), position.getZ() + 0.5D, 0.0F, 0.0F);
        unit.setNoAi(true);
        unit.setPersistenceRequired();
        unit.setVisualPose(EvaUnit01Entity.VISUAL_IDLE);
        level.addFreshEntity(unit);
        return unit;
    }

    static int pose(CommandSourceStack source, String name) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        EvaUnit01Entity unit = nearestUnit(player);
        int visualPose = switch (name)
        {
            case "normal" -> EvaUnit01Entity.VISUAL_NORMAL;
            case "idle" -> EvaUnit01Entity.VISUAL_IDLE;
            case "walk_contact" -> EvaUnit01Entity.VISUAL_WALK_CONTACT;
            case "knife_windup" -> EvaUnit01Entity.VISUAL_KNIFE_WINDUP;
            case "knife_contact" -> EvaUnit01Entity.VISUAL_KNIFE_CONTACT;
            case "knife_recovery" -> EvaUnit01Entity.VISUAL_KNIFE_RECOVERY;
            case "crouch" -> EvaUnit01Entity.VISUAL_CROUCH;
            case "prone" -> EvaUnit01Entity.VISUAL_PRONE;
            case "lance_windup" -> EvaUnit01Entity.VISUAL_LANCE_WINDUP;
            case "lance_contact" -> EvaUnit01Entity.VISUAL_LANCE_CONTACT;
            case "lance_recovery" -> EvaUnit01Entity.VISUAL_LANCE_RECOVERY;
            case "cannon" -> EvaUnit01Entity.VISUAL_CANNON;
            default -> throw new IllegalArgumentException("Unknown visual pose: " + name);
        };
        unit.setVisualPose(visualPose);
        unit.setYRot(0.0F);
        unit.setYBodyRot(0.0F);
        unit.setYHeadRot(0.0F);
        unit.setXRot(0.0F);
        unit.yRotO = 0.0F;
        unit.xRotO = 0.0F;
        source.sendSuccess(() -> Component.literal("Visual pose: " + name), false);
        return 1;
    }

    static int capture(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        EvaUnit01Entity unit = nearestUnit(player);
        if (player.getVehicle() != unit)
        {
            player.startRiding(unit, true);
        }
        player.setYRot(0.0F);
        player.setYHeadRot(0.0F);
        player.setXRot(0.0F);
        SeeleNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                new ClientboundVisualCapturePacket(unit.getId(), unit.getVisualPose()));
        source.sendSuccess(() -> Component.literal("Visual capture queued for Unit-01"), false);
        return 1;
    }

    private static EvaUnit01Entity nearestUnit(ServerPlayer player)
    {
        return player.serverLevel().getEntitiesOfClass(EvaUnit01Entity.class,
                        player.getBoundingBox().inflate(192.0D), Entity::isAlive).stream()
                .min((left, right) -> Double.compare(left.distanceToSqr(player), right.distanceToSqr(player)))
                .orElseThrow(() -> new IllegalStateException("No EVA within 192 blocks"));
    }

    private static void removeLabEntities(ServerLevel level, BlockPos centre)
    {
        AABB area = new AABB(centre).inflate(80.0D, 40.0D, 80.0D);
        level.getEntitiesOfClass(EvaUnit01Entity.class, area).forEach(Entity::discard);
        level.getEntitiesOfClass(ArmorStand.class, area,
                stand -> stand.hasCustomName() && "VISUAL TARGET".equals(stand.getCustomName().getString()))
                .forEach(Entity::discard);
    }
}
