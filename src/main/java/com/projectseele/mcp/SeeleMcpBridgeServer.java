package com.projectseele.mcp;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Semaphore;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;
import net.minecraft.server.MinecraftServer;

/** HTTP adapter used by the stdio MCP sidecar. */
final class SeeleMcpBridgeServer
{
    private static final Gson GSON = new Gson();
    private static final int MAX_BODY_BYTES = 4 * 1024 * 1024;
    private static final long SERVER_CALL_TIMEOUT_MS = 10_000L;

    private final MinecraftServer minecraftServer;
    private final int port;
    private final Semaphore requestSemaphore = new Semaphore(1);
    private HttpServer httpServer;
    private ExecutorService executor;

    SeeleMcpBridgeServer(MinecraftServer minecraftServer, int port)
    {
        this.minecraftServer = minecraftServer;
        this.port = port;
    }

    synchronized void start() throws IOException
    {
        if (httpServer != null)
        {
            return;
        }
        httpServer = HttpServer.create(new InetSocketAddress(
                InetAddress.getLoopbackAddress(), port), 0);
        executor = Executors.newCachedThreadPool(new BridgeThreadFactory());
        httpServer.setExecutor(executor);
        httpServer.createContext("/v1/health", this::handleHealth);
        httpServer.createContext("/v1/session", authenticated(
                exchange -> handleServerCall(exchange,
                        () -> SeeleMcpBuildService.session(minecraftServer))));
        httpServer.createContext("/v1/tools/buildsite", authenticated(
                exchange -> handleJsonCall(exchange,
                        body -> SeeleMcpBuildService.buildsite(
                                minecraftServer, body))));
        httpServer.createContext("/v1/tools/seele_status", authenticated(
                exchange -> handleServerCall(exchange,
                        () -> SeeleMcpBuildService.seeleStatus(
                                minecraftServer))));
        httpServer.createContext("/v1/tools/batch_status", authenticated(
                exchange -> handleJsonCall(exchange,
                        body -> SeeleMcpBuildService.batchStatus(body))));
        httpServer.createContext("/v1/actions/preview_build_plan", authenticated(
                exchange -> handleJsonCall(exchange,
                        body -> SeeleMcpBuildService.preview(
                                minecraftServer, body))));
        httpServer.createContext("/v1/actions/execute_build_plan", authenticated(
                exchange -> handleJsonCall(exchange,
                        body -> SeeleMcpBuildService.execute(
                                minecraftServer, body))));
        httpServer.createContext("/v1/actions/undo", authenticated(
                exchange -> handleServerCall(exchange,
                        () -> SeeleMcpBuildService.undo(minecraftServer))));
        httpServer.start();
    }

    synchronized void stop()
    {
        if (httpServer != null)
        {
            httpServer.stop(0);
            httpServer = null;
        }
        if (executor != null)
        {
            executor.shutdownNow();
            executor = null;
        }
    }

    private HttpHandler authenticated(HttpHandler handler)
    {
        return exchange ->
        {
            boolean acquired = false;
            try
            {
                if (!isLoopback(exchange))
                {
                    writeJson(exchange, 403,
                            error("FORBIDDEN",
                                    "The bridge accepts loopback requests only."));
                    return;
                }
                if (!isSupportedMethod(exchange))
                {
                    writeJson(exchange, 405,
                            error("METHOD_NOT_ALLOWED",
                                    "Only GET and POST are supported."));
                    return;
                }
                if (!isAuthorized(exchange))
                {
                    writeJson(exchange, 401,
                            error("UNAUTHORIZED",
                                    "Missing or invalid bearer token."));
                    return;
                }
                if (!SeeleMcpBridge.isEnabled())
                {
                    writeJson(exchange, 503,
                            error("BRIDGE_DISABLED",
                                    "Run /seele mcp enable in a trusted local world."));
                    return;
                }
                if (!requestSemaphore.tryAcquire())
                {
                    writeJson(exchange, 429,
                            error("BRIDGE_BUSY",
                                    "Another MCP request is running."));
                    return;
                }
                acquired = true;
                if (!SeeleMcpBridge.isServerResponsive())
                {
                    writeJson(exchange, 503,
                            error("SERVER_PAUSED",
                                    "Keep the single-player world open and unpaused."));
                    return;
                }
                handler.handle(exchange);
            }
            catch (RequestException exception)
            {
                writeJson(exchange, exception.status,
                        error(exception.code, exception.getMessage()));
            }
            catch (Throwable throwable)
            {
                ProjectSeele.LOGGER.warn("MCP request failed", throwable);
                writeJson(exchange, 500,
                        error("INTERNAL", "Bridge request failed: "
                                + throwable.getMessage()));
            }
            finally
            {
                if (acquired)
                {
                    requestSemaphore.release();
                }
            }
        };
    }

    private void handleHealth(HttpExchange exchange) throws IOException
    {
        if (!isLoopback(exchange))
        {
            writeJson(exchange, 403,
                    error("FORBIDDEN", "Loopback requests only."));
            return;
        }
        JsonObject result = new JsonObject();
        result.addProperty("ok", true);
        result.addProperty("project", "Project SEELE");
        result.addProperty("enabled", SeeleMcpBridge.isEnabled());
        result.addProperty("port", port);
        result.addProperty("loopbackOnly", true);
        result.addProperty("serverResponsive",
                SeeleMcpBridge.isServerResponsive());
        result.addProperty("busy", requestSemaphore.availablePermits() == 0);
        writeJson(exchange, 200, result);
    }

    private void handleServerCall(HttpExchange exchange,
                                  Supplier<JsonObject> action)
            throws IOException
    {
        JsonObject result = callOnServerThread(action);
        writeResult(exchange, result);
    }

    private void handleJsonCall(HttpExchange exchange,
                                JsonAction action) throws IOException
    {
        JsonObject body = readJsonBody(exchange);
        JsonObject result = callOnServerThread(() -> action.apply(body));
        writeResult(exchange, result);
    }

    private <T> T callOnServerThread(Supplier<T> action)
    {
        if (minecraftServer.isSameThread())
        {
            return action.get();
        }
        CompletableFuture<T> future = new CompletableFuture<>();
        minecraftServer.execute(() ->
        {
            try
            {
                future.complete(action.get());
            }
            catch (Throwable throwable)
            {
                future.completeExceptionally(throwable);
            }
        });
        try
        {
            return future.get(SERVER_CALL_TIMEOUT_MS, TimeUnit.MILLISECONDS);
        }
        catch (TimeoutException exception)
        {
            throw new RequestException(503, "SERVER_THREAD_TIMEOUT",
                    "Minecraft's server thread did not respond in time.");
        }
        catch (Exception exception)
        {
            throw new IllegalStateException(
                    "Server-thread MCP action failed", exception);
        }
    }

    private JsonObject readJsonBody(HttpExchange exchange) throws IOException
    {
        if ("GET".equalsIgnoreCase(exchange.getRequestMethod()))
        {
            return new JsonObject();
        }
        try (InputStream input = exchange.getRequestBody())
        {
            byte[] bytes = input.readNBytes(MAX_BODY_BYTES + 1);
            if (bytes.length > MAX_BODY_BYTES)
            {
                throw new RequestException(413, "BODY_TOO_LARGE",
                        "MCP request bodies are limited to 4 MiB.");
            }
            String raw = new String(bytes, StandardCharsets.UTF_8).trim();
            if (raw.isEmpty())
            {
                return new JsonObject();
            }
            try
            {
                JsonElement parsed = JsonParser.parseString(raw);
                if (!parsed.isJsonObject())
                {
                    throw new RequestException(400, "INVALID_JSON",
                            "The request body must be a JSON object.");
                }
                return parsed.getAsJsonObject();
            }
            catch (RequestException exception)
            {
                throw exception;
            }
            catch (RuntimeException exception)
            {
                throw new RequestException(400, "INVALID_JSON",
                        "Could not parse the JSON request body.");
            }
        }
    }

    private boolean isAuthorized(HttpExchange exchange)
    {
        String authorization = exchange.getRequestHeaders().getFirst(
                "Authorization");
        if (authorization == null || !authorization.startsWith("Bearer "))
        {
            return false;
        }
        byte[] supplied = authorization.substring("Bearer ".length()).trim()
                .getBytes(StandardCharsets.UTF_8);
        byte[] expected = SeeleMcpBridge.token()
                .getBytes(StandardCharsets.UTF_8);
        return expected.length > 0 && MessageDigest.isEqual(supplied, expected);
    }

    private static boolean isLoopback(HttpExchange exchange)
    {
        return exchange.getRemoteAddress() != null
                && exchange.getRemoteAddress().getAddress() != null
                && exchange.getRemoteAddress().getAddress().isLoopbackAddress();
    }

    private static boolean isSupportedMethod(HttpExchange exchange)
    {
        String method = exchange.getRequestMethod();
        return "GET".equalsIgnoreCase(method)
                || "POST".equalsIgnoreCase(method);
    }

    private static void writeResult(HttpExchange exchange, JsonObject result)
            throws IOException
    {
        if (result == null)
        {
            writeJson(exchange, 500,
                    error("INTERNAL", "No MCP result was produced."));
            return;
        }
        writeJson(exchange, result.has("error") ? 400 : 200, result);
    }

    private static JsonObject error(String code, String message)
    {
        JsonObject root = new JsonObject();
        JsonObject error = new JsonObject();
        error.addProperty("code", code);
        error.addProperty("message", message == null ? "Unknown error" : message);
        root.add("error", error);
        return root;
    }

    private static void writeJson(HttpExchange exchange, int status,
                                  JsonObject body) throws IOException
    {
        byte[] bytes = GSON.toJson(body).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set(
                "Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream output = exchange.getResponseBody())
        {
            output.write(bytes);
        }
    }

    @FunctionalInterface
    private interface JsonAction
    {
        JsonObject apply(JsonObject body);
    }

    private static final class RequestException extends RuntimeException
    {
        private final int status;
        private final String code;

        private RequestException(int status, String code, String message)
        {
            super(message);
            this.status = status;
            this.code = code;
        }
    }

    private static final class BridgeThreadFactory implements ThreadFactory
    {
        private int counter = 1;

        @Override
        public Thread newThread(Runnable runnable)
        {
            Thread thread = new Thread(runnable,
                    "projectseele-mcp-bridge-" + counter++);
            thread.setDaemon(true);
            return thread;
        }
    }
}
