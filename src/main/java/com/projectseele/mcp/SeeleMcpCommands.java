package com.projectseele.mcp;

import com.mojang.brigadier.CommandDispatcher;
import com.projectseele.ProjectSeele;
import com.projectseele.config.SeeleConfig;
import java.nio.file.Files;
import java.nio.file.Path;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.Style;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Operator-only lifecycle and setup commands for the local MCP bridge. */
@Mod.EventBusSubscriber(modid = ProjectSeele.MODID,
        bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class SeeleMcpCommands
{
    private SeeleMcpCommands() {}

    @SubscribeEvent
    public static void register(RegisterCommandsEvent event)
    {
        CommandDispatcher<CommandSourceStack> dispatcher =
                event.getDispatcher();
        dispatcher.register(Commands.literal("seele")
                .then(Commands.literal("mcp")
                        .requires(source -> source.hasPermission(4))
                        .then(Commands.literal("enable")
                                .executes(context -> enable(
                                        context.getSource(), true)))
                        .then(Commands.literal("disable")
                                .executes(context -> enable(
                                        context.getSource(), false)))
                        .then(Commands.literal("status")
                                .executes(context -> status(
                                        context.getSource())))
                        .then(Commands.literal("token")
                                .executes(context -> token(
                                        context.getSource(), false)))
                        .then(Commands.literal("regenerate-token")
                                .executes(context -> token(
                                        context.getSource(), true)))
                        .then(Commands.literal("setup")
                                .executes(context -> setup(
                                        context.getSource())))));
    }

    private static int enable(CommandSourceStack source, boolean enabled)
    {
        SeeleMcpBridge.setEnabled(enabled);
        source.sendSuccess(() -> Component.literal(
                enabled
                        ? "Project SEELE MCP enabled for this server run."
                        : "Project SEELE MCP disabled."), false);
        if (enabled)
        {
            source.sendSuccess(() -> Component.literal(
                    "Bridge: http://127.0.0.1:"
                            + SeeleConfig.MCP_PORT.get()
                            + " (loopback + bearer token)"),
                    false);
        }
        return 1;
    }

    private static int status(CommandSourceStack source)
    {
        String token = SeeleMcpBridge.token();
        String redacted = token.length() < 12 ? "not-ready"
                : token.substring(0, 6) + "..." + token.substring(
                token.length() - 4);
        source.sendSuccess(() -> Component.literal(
                "Project SEELE MCP: enabled=" + SeeleMcpBridge.isEnabled()
                        + ", responsive=" + SeeleMcpBridge.isServerResponsive()
                        + ", token=" + redacted), false);
        source.sendSuccess(() -> Component.literal(
                "Token file: " + SeeleMcpBridge.tokenPath()), false);
        return 1;
    }

    private static int token(CommandSourceStack source, boolean regenerate)
    {
        String value = regenerate ? SeeleMcpBridge.regenerateToken()
                : SeeleMcpBridge.token();
        Component copy = Component.literal("[Copy MCP token]")
                .withStyle(Style.EMPTY
                        .withColor(ChatFormatting.AQUA)
                        .withUnderlined(true)
                        .withClickEvent(new ClickEvent(
                                ClickEvent.Action.COPY_TO_CLIPBOARD, value))
                        .withHoverEvent(new HoverEvent(
                                HoverEvent.Action.SHOW_TEXT,
                                Component.literal("Copy the local bearer token"))));
        source.sendSuccess(() -> copy, false);
        if (regenerate)
        {
            source.sendSuccess(() -> Component.literal(
                    "Token regenerated. Restart connected MCP clients."), false);
        }
        return 1;
    }

    private static int setup(CommandSourceStack source)
    {
        Path projectRoot = locateProjectRoot();
        Path sidecar = projectRoot.resolve("tools/seele_mcp_sidecar.js");
        String command = "codex mcp add projectseele -- node \""
                + sidecar + "\" --project-root \"" + projectRoot + "\"";
        Component copy = Component.literal("[Copy Codex setup command]")
                .withStyle(Style.EMPTY
                        .withColor(ChatFormatting.GREEN)
                        .withUnderlined(true)
                        .withClickEvent(new ClickEvent(
                                ClickEvent.Action.COPY_TO_CLIPBOARD, command))
                        .withHoverEvent(new HoverEvent(
                                HoverEvent.Action.SHOW_TEXT,
                                Component.literal("Copy Codex MCP setup command"))));
        source.sendSuccess(() -> copy, false);
        source.sendSuccess(() -> Component.literal(command), false);
        return 1;
    }

    private static Path locateProjectRoot()
    {
        Path current = Path.of(System.getProperty("user.dir"))
                .toAbsolutePath().normalize();
        if (Files.isRegularFile(current.resolve(
                "tools/seele_mcp_sidecar.js")))
        {
            return current;
        }
        Path parent = current.getParent();
        if (parent != null && Files.isRegularFile(parent.resolve(
                "tools/seele_mcp_sidecar.js")))
        {
            return parent;
        }
        return current;
    }
}
