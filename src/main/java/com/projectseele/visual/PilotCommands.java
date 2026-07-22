package com.projectseele.visual;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.DoubleArgumentType;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.projectseele.ProjectSeele;
import com.projectseele.capability.EvaPilotCapability;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Operator-only inspection and acceleration for synchronization testing. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID, bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class PilotCommands
{
    private PilotCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("seele")
                .requires(source -> source.hasPermission(2))
                .then(Commands.literal("pilot")
                        .then(Commands.literal("sync")
                                .executes(context -> status(context.getSource()))
                                .then(Commands.literal("set")
                                        .then(Commands.argument("value",
                                                        DoubleArgumentType.doubleArg(0.0D, 100.0D))
                                                .executes(context -> set(context.getSource(),
                                                        DoubleArgumentType.getDouble(context,
                                                                "value"))))))));
    }

    private static int status(CommandSourceStack source) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        float value = EvaPilotCapability.synchronization(player);
        source.sendSuccess(() -> Component.literal(String.format(
                "Pilot synchronization: %.1f%%", value)), false);
        return Math.round(value * 10.0F);
    }

    private static int set(CommandSourceStack source, double value) throws CommandSyntaxException
    {
        ServerPlayer player = source.getPlayerOrException();
        player.getCapability(EvaPilotCapability.DATA).ifPresent(
                data -> data.setSynchronization((float) value));
        float applied = EvaPilotCapability.synchronization(player);
        source.sendSuccess(() -> Component.literal(String.format(
                "Pilot synchronization set to %.1f%%", applied)), true);
        return Math.round(applied * 10.0F);
    }
}