package com.projectseele.mcp;

import com.projectseele.ProjectSeele;
import com.projectseele.config.SeeleConfig;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.security.SecureRandom;
import net.minecraft.server.MinecraftServer;
import net.minecraftforge.fml.loading.FMLPaths;

/**
 * Lifecycle and credentials for the loopback-only Project SEELE MCP bridge.
 *
 * <p>The bridge deliberately starts disabled by default. It never listens on
 * a non-loopback address and every world-facing endpoint requires the bearer
 * token written to the local Forge config directory.</p>
 */
public final class SeeleMcpBridge
{
    public static final String TOKEN_FILE_NAME = "projectseele-mcp-token.txt";

    private static final SecureRandom RANDOM = new SecureRandom();
    private static volatile SeeleMcpBridgeServer bridgeServer;
    private static volatile MinecraftServer activeServer;
    private static volatile String token = "";
    private static volatile boolean enabled;
    private static volatile long lastServerTickMs;
    private static volatile long lastStartAttemptMs;

    private SeeleMcpBridge() {}

    public static synchronized void start(MinecraftServer server)
    {
        if (server == null || activeServer == server && bridgeServer != null)
        {
            return;
        }
        boolean requestedEnabled = activeServer == server
                ? enabled : SeeleConfig.MCP_ENABLED.get();
        stopInternal(false);
        lastStartAttemptMs = System.currentTimeMillis();
        activeServer = server;
        enabled = requestedEnabled;
        token = loadOrCreateToken();
        try
        {
            bridgeServer = new SeeleMcpBridgeServer(
                    server, SeeleConfig.MCP_PORT.get());
            bridgeServer.start();
            ProjectSeele.LOGGER.info(
                    "Project SEELE MCP bridge listening on 127.0.0.1:{} (enabled={})",
                    SeeleConfig.MCP_PORT.get(), enabled);
        }
        catch (IOException exception)
        {
            bridgeServer = null;
            ProjectSeele.LOGGER.error(
                    "Project SEELE MCP bridge could not start on port {}",
                    SeeleConfig.MCP_PORT.get(), exception);
        }
    }

    public static void tick(MinecraftServer server)
    {
        lastServerTickMs = System.currentTimeMillis();
        if (activeServer != server
                || bridgeServer == null
                && System.currentTimeMillis() - lastStartAttemptMs >= 5_000L)
        {
            start(server);
        }
        SeeleMcpBuildService.tick(server);
    }

    public static synchronized void stop(MinecraftServer server)
    {
        if (server != null && activeServer != null && activeServer != server)
        {
            return;
        }
        SeeleMcpBuildService.shutdown(server);
        stopInternal(true);
    }

    private static void stopInternal(boolean clearAttemptTime)
    {
        if (bridgeServer != null)
        {
            bridgeServer.stop();
        }
        bridgeServer = null;
        activeServer = null;
        enabled = false;
        lastServerTickMs = 0L;
        if (clearAttemptTime)
        {
            lastStartAttemptMs = 0L;
        }
    }

    public static boolean isEnabled()
    {
        return enabled;
    }

    public static void setEnabled(boolean value)
    {
        enabled = value;
        ProjectSeele.LOGGER.info("Project SEELE MCP bridge enabled={}", value);
    }

    public static synchronized String regenerateToken()
    {
        token = generateToken();
        writeToken(token);
        return token;
    }

    public static String token()
    {
        return token;
    }

    public static Path tokenPath()
    {
        return FMLPaths.CONFIGDIR.get().resolve(TOKEN_FILE_NAME).toAbsolutePath();
    }

    public static long lastServerTickMs()
    {
        return lastServerTickMs;
    }

    public static boolean isServerResponsive()
    {
        long tick = lastServerTickMs;
        return activeServer != null && tick > 0L
                && System.currentTimeMillis() - tick <= 2_500L;
    }

    private static String loadOrCreateToken()
    {
        Path path = tokenPath();
        try
        {
            if (Files.isRegularFile(path))
            {
                String existing = Files.readString(path, StandardCharsets.UTF_8).trim();
                if (existing.matches("[0-9a-f]{64}"))
                {
                    return existing;
                }
            }
        }
        catch (IOException exception)
        {
            ProjectSeele.LOGGER.warn("Could not read MCP token file {}", path,
                    exception);
        }
        String generated = generateToken();
        writeToken(generated);
        return generated;
    }

    private static void writeToken(String value)
    {
        Path path = tokenPath();
        try
        {
            Files.createDirectories(path.getParent());
            Files.writeString(path, value + System.lineSeparator(),
                    StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE,
                    StandardOpenOption.TRUNCATE_EXISTING,
                    StandardOpenOption.WRITE);
            try
            {
                Files.setPosixFilePermissions(path,
                        PosixFilePermissions.fromString("rw-------"));
            }
            catch (UnsupportedOperationException ignored)
            {
                // Windows has no POSIX mode bits; the user profile ACL applies.
            }
            catch (IOException permissionException)
            {
                ProjectSeele.LOGGER.warn(
                        "Could not restrict MCP token file permissions for {}",
                        path, permissionException);
            }
        }
        catch (IOException exception)
        {
            throw new IllegalStateException(
                    "Could not write MCP token file " + path, exception);
        }
    }

    private static String generateToken()
    {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        StringBuilder result = new StringBuilder(bytes.length * 2);
        for (byte value : bytes)
        {
            result.append(String.format("%02x", value & 0xFF));
        }
        return result.toString();
    }
}
