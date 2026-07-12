package com.projectseele.client.render;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Function;
import java.util.function.BiPredicate;
import java.util.zip.CRC32;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.core.animatable.GeoAnimatable;
import software.bernie.geckolib.renderer.GeoRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

/**
 * Optional local-only triangle geometry driven by a GeckoLib bone hierarchy.
 * The public jar contains the loader but no third-party mesh or texture.
 */
public final class LocalTriangleMeshLayer<T extends GeoAnimatable> extends GeoRenderLayer<T>
{
    private static final Map<ResourceLocation, MeshData> CACHE = new HashMap<>();
    private static final Set<ResourceLocation> LOAD_ATTEMPTED = new HashSet<>();
    private final Function<T, ResourceLocation> meshSelector;
    private final Function<T, ResourceLocation> textureSelector;
    private final BiPredicate<T, GeoBone> partVisibility;

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector)
    {
        this(renderer, meshSelector, null, (entity, bone) -> true);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector)
    {
        this(renderer, meshSelector, textureSelector, (entity, bone) -> true);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector,
                                  BiPredicate<T, GeoBone> partVisibility)
    {
        super(renderer);
        this.meshSelector = meshSelector;
        this.textureSelector = textureSelector;
        this.partVisibility = partVisibility;
    }

    @Override
    public void renderForBone(PoseStack poseStack, T animatable, GeoBone bone,
                              RenderType renderType, MultiBufferSource bufferSource,
                              VertexConsumer buffer, float partialTick, int packedLight,
                              int packedOverlay)
    {
        if (bone.isHidden() || !this.partVisibility.test(animatable, bone))
        {
            return;
        }
        MeshData mesh = getMesh(this.meshSelector.apply(animatable));
        if (mesh == null)
        {
            return;
        }
        MeshPart part = mesh.parts().get(bone.getName());
        if (part == null)
        {
            return;
        }

        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        VertexConsumer targetBuffer = this.textureSelector == null ? buffer
                : bufferSource.getBuffer(RenderType.entityCutoutNoCull(
                        this.textureSelector.apply(animatable)));
        float[] values = part.vertices();
        int stride = mesh.stride();
        for (int index = 0; index + stride * 3 <= values.length; index += stride * 3)
        {
            emitVertex(targetBuffer, pose, normal, values, index, part, packedLight, packedOverlay);
            emitVertex(targetBuffer, pose, normal, values, index + stride, part,
                    packedLight, packedOverlay);
            emitVertex(targetBuffer, pose, normal, values, index + stride * 2, part,
                    packedLight, packedOverlay);
            // Gecko's entity cutout buffer is QUADS. A repeated third point
            // makes each OBJ triangle an independent degenerate quad.
            emitVertex(targetBuffer, pose, normal, values, index + stride * 2, part,
                    packedLight, packedOverlay);
        }
    }

    private static void emitVertex(VertexConsumer buffer, Matrix4f pose, Matrix3f normal,
                                   float[] values, int index, MeshPart part,
                                   int packedLight, int packedOverlay)
    {
        // Match GeckoLib's Bedrock X reflection so cubes and local triangles
        // occupy the same animated coordinate space.
        float x = -(values[index] + part.pivotX()) / 16.0F;
        float y = (values[index + 1] + part.pivotY()) / 16.0F;
        float z = (values[index + 2] + part.pivotZ()) / 16.0F;
        buffer.vertex(pose, x, y, z)
                .color(255, 255, 255, 255)
                .uv(values[index + 3], values[index + 4])
                .overlayCoords(packedOverlay)
                .uv2(packedLight)
                .normal(normal, -values[index + 5], values[index + 6], values[index + 7])
                .endVertex();
    }

    public static void clearCache()
    {
        CACHE.clear();
        LOAD_ATTEMPTED.clear();
    }

    public static boolean hasPart(ResourceLocation meshResource, String boneName)
    {
        MeshData mesh = getMesh(meshResource);
        return mesh != null && mesh.parts().containsKey(boneName);
    }

    public static String captureTag(ResourceLocation meshResource)
    {
        MeshData mesh = getMesh(meshResource);
        return mesh == null ? "mesh-missing" : mesh.captureTag();
    }

    private static MeshData getMesh(ResourceLocation meshLocation)
    {
        if (LOAD_ATTEMPTED.contains(meshLocation))
        {
            return CACHE.get(meshLocation);
        }
        LOAD_ATTEMPTED.add(meshLocation);
        Optional<Resource> resource = Minecraft.getInstance().getResourceManager()
                .getResource(meshLocation);
        if (resource.isEmpty())
        {
            return null;
        }
        try (var stream = resource.get().open())
        {
            byte[] bytes = stream.readAllBytes();
            JsonObject root = JsonParser.parseString(
                    new String(bytes, StandardCharsets.UTF_8)).getAsJsonObject();
            int stride = root.get("stride").getAsInt();
            if (stride != 8)
            {
                throw new IOException("Unsupported local mesh stride " + stride);
            }
            Map<String, MeshPart> parts = new HashMap<>();
            for (Map.Entry<String, JsonElement> entry : root.getAsJsonObject("parts").entrySet())
            {
                JsonObject object = entry.getValue().getAsJsonObject();
                JsonArray pivot = object.getAsJsonArray("pivot");
                JsonArray source = object.getAsJsonArray("vertices");
                if (pivot.size() != 3 || source.size() == 0)
                {
                    throw new IOException("Invalid local mesh part " + entry.getKey());
                }
                float[] vertices = new float[source.size()];
                for (int index = 0; index < source.size(); index++)
                {
                    vertices[index] = source.get(index).getAsFloat();
                    if (!Float.isFinite(vertices[index]))
                    {
                        throw new IOException("Non-finite vertex in " + entry.getKey());
                    }
                }
                if (vertices.length % (stride * 3) != 0)
                {
                    throw new IOException("Incomplete triangles in " + entry.getKey());
                }
                parts.put(entry.getKey(), new MeshPart(
                        pivot.get(0).getAsFloat(), pivot.get(1).getAsFloat(),
                        pivot.get(2).getAsFloat(), vertices));
            }
            int triangleCount = parts.values().stream()
                    .mapToInt(part -> part.vertices().length / (stride * 3)).sum();
            CRC32 crc = new CRC32();
            crc.update(bytes);
            String captureTag = String.format("triangle-mesh-%d-p%d-%08x",
                    triangleCount, parts.size(), crc.getValue());
            MeshData mesh = new MeshData(stride, Map.copyOf(parts), triangleCount,
                    captureTag);
            CACHE.put(meshLocation, mesh);
            ProjectSeele.LOGGER.info("Loaded local triangle mesh {}: {}",
                    meshLocation, captureTag);
            return mesh;
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("Failed to load local triangle mesh " + meshLocation,
                    exception);
            return null;
        }
    }

    private record MeshData(int stride, Map<String, MeshPart> parts, int triangleCount,
                            String captureTag) {}

    private record MeshPart(float pivotX, float pivotY, float pivotZ, float[] vertices) {}
}
