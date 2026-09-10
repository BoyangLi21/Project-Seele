package com.projectseele.visual;

import com.projectseele.ProjectSeele;
import com.projectseele.world.NervStaffDialogue;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.commands.Commands;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class NervStaffCommands
{
    @SubscribeEvent public static void register(RegisterCommandsEvent event)
    {
        event.getDispatcher().register(Commands.literal("nerv").then(Commands.literal("talk")
                .then(Commands.argument("person",StringArgumentType.string()).then(Commands.argument("message",StringArgumentType.greedyString())
                        .executes(c->NervStaffDialogue.talk(c.getSource().getPlayerOrException(),StringArgumentType.getString(c,"person"),StringArgumentType.getString(c,"message")))))));
    }
    private NervStaffCommands() {}
}
