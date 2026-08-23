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
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
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
    private final boolean fullBright;

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector)
    {
        this(renderer, meshSelector, null, (entity, bone) -> true, false);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector)
    {
        this(renderer, meshSelector, textureSelector,
                (entity, bone) -> true, false);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector,
                                  BiPredicate<T, GeoBone> partVisibility)
    {
        this(renderer, meshSelector, textureSelector, partVisibility, false);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector,
                                  BiPredicate<T, GeoBone> partVisibility,
                                  boolean fullBright)
    {
        super(renderer);
        this.meshSelector = meshSelector;
        this.textureSelector = textureSelector;
        this.partVisibility = partVisibility;
        this.fullBright = fullBright;
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
        ResourceLocation meshLocation = this.meshSelector.apply(animatable);
        MeshData mesh = getMesh(meshLocation);
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
        if (animatable instanceof EvaUnit01Entity eva
                && eva.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                && "cannon".equals(bone.getName())
                && meshLocation.getPath().endsWith("eva_pallet_smg.mesh.json"))
        {
            Vector3f rendered = pose.transformPosition(new Vector3f(
                    part.muzzleX(), part.muzzleY(), part.muzzleZ()));
            Vec3 camera = Minecraft.getInstance().gameRenderer
                    .getMainCamera().getPosition();
            EvaUnit01Renderer.rememberRifleMuzzle(eva.getId(),
                    camera.add(rendered.x, rendered.y, rendered.z));
        }
        VertexConsumer targetBuffer = this.textureSelector == null ? buffer
                : bufferSource.getBuffer(RenderType.entityCutoutNoCull(
                        this.textureSelector.apply(animatable)));
        float[] values = part.vertices();
        int stride = mesh.stride();
        int vertexLight = this.fullBright
                ? LightTexture.FULL_BRIGHT : packedLight;
        for (int index = 0; index + stride * 3 <= values.length; index += stride * 3)
        {
            emitVertex(targetBuffer, pose, normal, values, index, part,
                    vertexLight, packedOverlay);
            emitVertex(targetBuffer, pose, normal, values, index + stride, part,
                    vertexLight, packedOverlay);
            emitVertex(targetBuffer, pose, normal, values, index + stride * 2, part,
                    vertexLight, packedOverlay);
            // Gecko's entity cutout buffer is QUADS. A repeated third point
            // makes each OBJ triangle an independent degenerate quad.
            emitVertex(targetBuffer, pose, normal, values, index + stride * 2, part,
                    vertexLight, packedOverlay);
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

    /**
     * Parses the large local EVA shells while the resource reload screen still
     * owns the render thread. Lazy parsing after an EVA first enters view can
     * otherwise create multi-second frame stalls in an ordinary route walk.
     */
    public static void prewarm(ResourceManager resourceManager,
                               ResourceLocation... meshResources)
    {
        long startedAt = System.nanoTime();
        int loaded = 0;
        for (ResourceLocation meshResource : meshResources)
        {
            if (getMesh(resourceManager, meshResource) != null)
            {
                loaded++;
            }
        }
        ProjectSeele.LOGGER.info(
                "Prewarmed local triangle meshes: loaded={}/{} elapsedMs={}",
                loaded, meshResources.length,
                (System.nanoTime() - startedAt) / 1_000_000L);
    }

    public static boolean hasPart(ResourceLocation meshResource, String boneName)
    {
        MeshData mesh = getMesh(meshResource);
        return mesh != null && mesh.parts().containsKey(boneName);
    }

    /**
     * Renders a local attachment mesh as one independent world object.
     * Weapon elevators use this path so the payload stays a real persistent
     * entity before it is handed to the EVA skeleton.  The mesh is centred on
     * X/Z and rests on local Y=0; caller scale/orientation remains explicit.
     */
    public static boolean renderStandalone(PoseStack poseStack,
                                           MultiBufferSource bufferSource,
                                           ResourceLocation meshResource,
                                           ResourceLocation textureResource,
                                           int packedLight,
                                           int packedOverlay)
    {
        MeshData mesh = getMesh(meshResource);
        if (mesh == null)
        {
            return false;
        }
        VertexConsumer target = bufferSource.getBuffer(
                RenderType.entityCutoutNoCull(textureResource));
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        for (MeshPart part : mesh.parts().values())
        {
            float[] values = part.vertices();
            for (int index = 0; index + mesh.stride() * 3 <= values.length;
                 index += mesh.stride() * 3)
            {
                emitStandaloneVertex(target, pose, normal, values, index,
                        part, mesh, packedLight, packedOverlay);
                emitStandaloneVertex(target, pose, normal, values,
                        index + mesh.stride(), part, mesh,
                        packedLight, packedOverlay);
                emitStandaloneVertex(target, pose, normal, values,
                        index + mesh.stride() * 2, part, mesh,
                        packedLight, packedOverlay);
                emitStandaloneVertex(target, pose, normal, values,
                        index + mesh.stride() * 2, part, mesh,
                        packedLight, packedOverlay);
            }
        }
        return true;
    }

    private static void emitStandaloneVertex(VertexConsumer buffer,
                                             Matrix4f pose, Matrix3f normal,
                                             float[] values, int index,
                                             MeshPart part, MeshData mesh,
                                             int packedLight,
                                             int packedOverlay)
    {
        float absoluteX = values[index] + part.pivotX();
        float absoluteY = values[index + 1] + part.pivotY();
        float absoluteZ = values[index + 2] + part.pivotZ();
        float x = -(absoluteX - mesh.centreX()) / 16.0F;
        float y = (absoluteY - mesh.minimumY()) / 16.0F;
        float z = (absoluteZ - mesh.centreZ()) / 16.0F;
        buffer.vertex(pose, x, y, z)
                .color(255, 255, 255, 255)
                .uv(values[index + 3], values[index + 4])
                .overlayCoords(packedOverlay)
                .uv2(packedLight)
                .normal(normal, -values[index + 5], values[index + 6],
                        values[index + 7])
                .endVertex();
    }

    public static String captureTag(ResourceLocation meshResource)
    {
        MeshData mesh = getMesh(meshResource);
        return mesh == null ? "mesh-missing" : mesh.captureTag();
    }

    private static MeshData getMesh(ResourceLocation meshLocation)
    {
        return getMesh(Minecraft.getInstance().getResourceManager(),
                meshLocation);
    }

    private static MeshData getMesh(ResourceManager resourceManager,
                                    ResourceLocation meshLocation)
    {
        if (LOAD_ATTEMPTED.contains(meshLocation))
        {
            return CACHE.get(meshLocation);
        }
        LOAD_ATTEMPTED.add(meshLocation);
        Optional<Resource> resource = resourceManager.getResource(meshLocation);
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
                float pivotX = pivot.get(0).getAsFloat();
                float pivotY = pivot.get(1).getAsFloat();
                float pivotZ = pivot.get(2).getAsFloat();
                float[] muzzle = farCap(vertices, stride,
                        pivotX, pivotY, pivotZ);
                parts.put(entry.getKey(), new MeshPart(
                        pivotX, pivotY, pivotZ, vertices,
                        muzzle[0], muzzle[1], muzzle[2]));
            }
            int triangleCount = parts.values().stream()
                    .mapToInt(part -> part.vertices().length / (stride * 3)).sum();
            CRC32 crc = new CRC32();
            crc.update(bytes);
            String captureTag = String.format("triangle-mesh-%d-p%d-%08x",
                    triangleCount, parts.size(), crc.getValue());
            float minimumX = Float.POSITIVE_INFINITY;
            float minimumY = Float.POSITIVE_INFINITY;
            float minimumZ = Float.POSITIVE_INFINITY;
            float maximumX = Float.NEGATIVE_INFINITY;
            float maximumZ = Float.NEGATIVE_INFINITY;
            for (MeshPart part : parts.values())
            {
                float[] values = part.vertices();
                for (int index = 0; index < values.length; index += stride)
                {
                    float x = values[index] + part.pivotX();
                    float y = values[index + 1] + part.pivotY();
                    float z = values[index + 2] + part.pivotZ();
                    minimumX = Math.min(minimumX, x);
                    minimumY = Math.min(minimumY, y);
                    minimumZ = Math.min(minimumZ, z);
                    maximumX = Math.max(maximumX, x);
                    maximumZ = Math.max(maximumZ, z);
                }
            }
            MeshData mesh = new MeshData(stride, Map.copyOf(parts),
                    triangleCount, captureTag,
                    (minimumX + maximumX) * 0.5F, minimumY,
                    (minimumZ + maximumZ) * 0.5F);
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

    private static float[] farCap(float[] vertices, int stride,
                                  float pivotX, float pivotY, float pivotZ)
    {
        float minimumY = Float.POSITIVE_INFINITY;
        for (int index = 0; index < vertices.length; index += stride)
        {
            minimumY = Math.min(minimumY, vertices[index + 1]);
        }
        float sumX = 0.0F;
        float sumY = 0.0F;
        float sumZ = 0.0F;
        int samples = 0;
        for (int index = 0; index < vertices.length; index += stride)
        {
            if (vertices[index + 1] > minimumY + 0.85F)
            {
                continue;
            }
            sumX += vertices[index] + pivotX;
            sumY += vertices[index + 1] + pivotY;
            sumZ += vertices[index + 2] + pivotZ;
            samples++;
        }
        if (samples == 0)
        {
            return new float[] {-pivotX / 16.0F,
                    pivotY / 16.0F, pivotZ / 16.0F};
        }
        return new float[] {-(sumX / samples) / 16.0F,
                (sumY / samples) / 16.0F,
                (sumZ / samples) / 16.0F};
    }

    private record MeshData(int stride, Map<String, MeshPart> parts,
                            int triangleCount, String captureTag,
                            float centreX, float minimumY,
                            float centreZ) {}

    private record MeshPart(float pivotX, float pivotY, float pivotZ,
                            float[] vertices, float muzzleX,
                            float muzzleY, float muzzleZ) {}
}
