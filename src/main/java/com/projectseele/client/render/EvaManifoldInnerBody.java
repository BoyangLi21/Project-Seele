package com.projectseele.client.render;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;

/** Phase-E single-component inner body, isolated from the live Tiger body. */
public final class EvaManifoldInnerBody
{
    private static final ResourceLocation CONTRACT = new ResourceLocation(
            ProjectSeele.MODID, "eva/eva_manifold_inner_contract.json");
    private static final ResourceLocation BODY = new ResourceLocation(
            ProjectSeele.MODID,
            "eva/eva_unit01_manifold_inner.skinned.json");
    private static final ResourceLocation MASKS = new ResourceLocation(
            ProjectSeele.MODID, "eva/eva_unit01_rigid_shell_masks.json");
    private static volatile EvaSkinnedMeshRuntime.MeshData mesh;
    private static volatile Status status = Status.missing();
    private static boolean firstRenderLogged;

    private EvaManifoldInnerBody() {}

    public static void reload(ResourceManager resources)
    {
        mesh = null;
        firstRenderLogged = false;
        try
        {
            String contractText = read(resources, CONTRACT);
            String bodyText = read(resources, BODY);
            String maskText = read(resources, MASKS);
            JsonObject contract = JsonParser.parseString(
                    contractText).getAsJsonObject();
            JsonObject body = JsonParser.parseString(
                    bodyText).getAsJsonObject();
            JsonObject masks = JsonParser.parseString(
                    maskText).getAsJsonObject();
            validateContract(contract, body, masks);
            EvaSkinnedMeshRuntime.MeshData loaded =
                    EvaSkinnedMeshRuntime.load(resources, BODY);
            JsonObject expected = contract.getAsJsonObject("expected");
            JsonObject manifold = body.getAsJsonObject("manifold");
            require(loaded.palette().size() ==
                    expected.get("paletteBones").getAsInt(),
                    "manifold palette count differs");
            require(loaded.vertices().size() ==
                    expected.get("vertices").getAsInt(),
                    "manifold vertex count differs");
            require(loaded.indices().length / 3 ==
                    expected.get("triangles").getAsInt(),
                    "manifold triangle count differs");
            mesh = loaded;
            status = new Status(true, previewEnabled(),
                    loaded.palette().size(),
                    manifold.get("primitiveCount").getAsInt(),
                    loaded.vertices().size(), loaded.indices().length / 3,
                    manifold.get("components").getAsInt(),
                    manifold.get("nonManifoldEdges").getAsInt(),
                    manifold.get("eulerCharacteristic").getAsInt(),
                    masks.get("sourcePartCount").getAsInt(),
                    masks.get("sourceTriangleCount").getAsInt(),
                    sha256(contractText), sha256(bodyText),
                    sha256(maskText), 0L, -1, -1.0F, "none");
            ProjectSeele.LOGGER.info(
                    "EVA manifold inner body loaded: palette={} primitives={} "
                            + "vertices={} triangles={} components={} "
                            + "nonManifoldEdges={} euler={} rigidParts={} "
                            + "rigidTriangles={} previewEnabled={} "
                            + "replacesTiger=false",
                    status.paletteBones(), status.primitives(),
                    status.vertices(), status.triangles(),
                    status.components(), status.nonManifoldEdges(),
                    status.eulerCharacteristic(), status.rigidParts(),
                    status.rigidTriangles(), status.previewEnabled());
        }
        catch (Exception exception)
        {
            status = Status.failed(exception.getMessage());
            ProjectSeele.LOGGER.error(
                    "EVA manifold inner body rejected", exception);
        }
    }

    public static void prepare(BakedGeoModel model)
    {
        EvaSkinnedMeshRuntime.MeshData current = mesh;
        if (!previewEnabled() || current == null)
        {
            return;
        }
        for (String name : current.palette())
        {
            model.getBone(name).ifPresent(bone ->
                    bone.setTrackingMatrices(true));
        }
    }

    public static void renderAfterRoot(PoseStack poseStack,
                                       EvaUnit01Entity entity,
                                       GeoBone root,
                                       MultiBufferSource bufferSource,
                                       int packedLight, int packedOverlay)
    {
        EvaSkinnedMeshRuntime.MeshData current = mesh;
        if (!previewEnabled() || current == null
                || entity.getUnitVariant() != EvaUnit01Entity.UNIT_01)
        {
            return;
        }
        Map<String, GeoBone> bones = new HashMap<>();
        collect(root, bones);
        Matrix4f[] palette = new Matrix4f[current.palette().size()];
        for (int index = 0; index < palette.length; index++)
        {
            String name = current.palette().get(index);
            GeoBone bone = bones.get(name);
            if (bone == null || !bone.isTrackingMatrices())
            {
                status = status.withFailure(
                        "missing tracked manifold bone " + name);
                return;
            }
            palette[index] = new Matrix4f(bone.getModelSpaceMatrix());
        }
        try
        {
            float[] positions = EvaSkinnedMeshRuntime.skinPositions(
                    current, palette);
            Vector3f[] normals = EvaSkinnedMeshRuntime.skinNormals(
                    current, palette);
            VertexConsumer target = bufferSource.getBuffer(
                    RenderType.entityTranslucent(
                            EvaUnit01Renderer.textureResourceForVariant(
                                    entity.getUnitVariant())));
            Matrix4f pose = poseStack.last().pose();
            Matrix3f normal = poseStack.last().normal();
            int[] indices = current.indices();
            for (int index = 0; index < indices.length; index += 3)
            {
                emit(target, pose, normal, current, positions, normals,
                        indices[index], packedLight, packedOverlay);
                emit(target, pose, normal, current, positions, normals,
                        indices[index + 1], packedLight, packedOverlay);
                emit(target, pose, normal, current, positions, normals,
                        indices[index + 2], packedLight, packedOverlay);
                emit(target, pose, normal, current, positions, normals,
                        indices[index + 2], packedLight, packedOverlay);
            }
            float bindDelta = maximumBindDelta(current, positions);
            status = status.withRender(entity.getId(), bindDelta);
            if (!firstRenderLogged)
            {
                firstRenderLogged = true;
                ProjectSeele.LOGGER.info(
                        "EVA manifold inner body rendered after recursion: "
                                + "entity={} palette={} vertices={} "
                                + "triangles={} bindDelta={} "
                                + "replacesTiger=false",
                        entity.getId(), current.palette().size(),
                        current.vertices().size(), indices.length / 3,
                        bindDelta);
            }
        }
        catch (Exception exception)
        {
            status = status.withFailure(exception.getMessage());
            ProjectSeele.LOGGER.error(
                    "EVA manifold inner body render failed", exception);
        }
    }

    public static boolean previewEnabled()
    {
        return Boolean.getBoolean("projectseele.manifoldInnerPreview");
    }

    public static Status status()
    {
        return status;
    }

    private static void emit(VertexConsumer target, Matrix4f pose,
                             Matrix3f normalMatrix,
                             EvaSkinnedMeshRuntime.MeshData meshData,
                             float[] positions, Vector3f[] normals,
                             int vertexIndex, int packedLight,
                             int packedOverlay)
    {
        int offset = vertexIndex * 3;
        EvaSkinnedMeshRuntime.VertexData source =
                meshData.vertices().get(vertexIndex);
        Vector3f normal = normals[vertexIndex];
        target.vertex(pose, positions[offset], positions[offset + 1],
                        positions[offset + 2])
                .color(128, 255, 128, 106)
                .uv(source.u(), source.v())
                .overlayCoords(packedOverlay)
                .uv2(packedLight)
                .normal(normalMatrix, normal.x, normal.y, normal.z)
                .endVertex();
    }

    private static void collect(GeoBone bone, Map<String, GeoBone> target)
    {
        target.put(bone.getName(), bone);
        for (GeoBone child : bone.getChildBones())
        {
            collect(child, target);
        }
    }

    private static float maximumBindDelta(
            EvaSkinnedMeshRuntime.MeshData meshData, float[] positions)
    {
        float maximum = 0.0F;
        for (int index = 0; index < meshData.vertices().size(); index++)
        {
            Vector3f bind = meshData.vertices().get(index).position();
            int offset = index * 3;
            maximum = Math.max(maximum, Math.abs(
                    bind.x - positions[offset]));
            maximum = Math.max(maximum, Math.abs(
                    bind.y - positions[offset + 1]));
            maximum = Math.max(maximum, Math.abs(
                    bind.z - positions[offset + 2]));
        }
        return maximum;
    }

    private static void validateContract(JsonObject contract,
                                         JsonObject body,
                                         JsonObject masks)
    {
        require(contract.get("schema").getAsInt() == 1
                && "E".equals(contract.get("phase").getAsString()),
                "manifold contract schema or phase differs");
        require("MANIFOLD_INNER_AND_RIGID_MASK_RESEARCH".equals(
                contract.get("status").getAsString()),
                "manifold contract is not research-only");
        JsonObject activation = contract.getAsJsonObject(
                "runtimeActivation");
        require(!activation.get("defaultEnabled").getAsBoolean()
                && !activation.get("replacesTigerBody").getAsBoolean()
                && !activation.get("productionReady").getAsBoolean()
                && activation.get(
                "humanReviewRequiredBeforePromotion").getAsBoolean(),
                "manifold body escaped isolation");
        require("RESEARCH_MANIFOLD_NOT_LIVE_BODY".equals(
                body.get("status").getAsString()),
                "manifold resource claims live status");
        JsonObject manifold = body.getAsJsonObject("manifold");
        require(manifold.get("components").getAsInt() == 1
                && manifold.get("nonManifoldEdges").getAsInt() == 0
                && manifold.get("eulerCharacteristic").getAsInt() == 2,
                "manifold topology metadata is invalid");
        require("TIGER_SINGLE_OWNER_SHELL_MASK".equals(
                masks.get("status").getAsString()),
                "Tiger rigid mask status differs");
        JsonObject expected = contract.getAsJsonObject("expected");
        require(masks.get("sourcePartCount").getAsInt() ==
                expected.get("rigidParts").getAsInt()
                && masks.get("sourceTriangleCount").getAsInt() ==
                expected.get("rigidTriangles").getAsInt(),
                "Tiger rigid mask counts differ");
    }

    private static String read(ResourceManager resources,
                               ResourceLocation location) throws Exception
    {
        try (InputStream stream = resources.getResource(location)
                .orElseThrow(() -> new IllegalStateException(
                        "missing manifold inner resource " + location)).open())
        {
            return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private static String sha256(String text) throws Exception
    {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return HexFormat.of().formatHex(digest.digest(
                text.getBytes(StandardCharsets.UTF_8)));
    }

    private static void require(boolean condition, String message)
    {
        if (!condition) throw new IllegalArgumentException(message);
    }

    public record Status(boolean ready, boolean previewEnabled,
                         int paletteBones, int primitives, int vertices,
                         int triangles, int components,
                         int nonManifoldEdges, int eulerCharacteristic,
                         int rigidParts, int rigidTriangles,
                         String contractSha256, String bodySha256,
                         String maskSha256, long renderedFrames,
                         int lastEntityId, float lastBindDelta,
                         String failure)
    {
        private static Status missing()
        {
            return failed("not_loaded");
        }

        private static Status failed(String reason)
        {
            return new Status(false,
                    EvaManifoldInnerBody.previewEnabled(),
                    0, 0, 0, 0, 0, 0, 0, 0, 0,
                    "missing", "missing", "missing", 0L, -1, -1.0F,
                    reason == null ? "failed" : reason);
        }

        private Status withRender(int entityId, float bindDelta)
        {
            return new Status(this.ready,
                    EvaManifoldInnerBody.previewEnabled(),
                    this.paletteBones, this.primitives, this.vertices,
                    this.triangles, this.components,
                    this.nonManifoldEdges, this.eulerCharacteristic,
                    this.rigidParts, this.rigidTriangles,
                    this.contractSha256, this.bodySha256, this.maskSha256,
                    this.renderedFrames + 1L, entityId, bindDelta, "none");
        }

        private Status withFailure(String reason)
        {
            return new Status(false,
                    EvaManifoldInnerBody.previewEnabled(),
                    this.paletteBones, this.primitives, this.vertices,
                    this.triangles, this.components,
                    this.nonManifoldEdges, this.eulerCharacteristic,
                    this.rigidParts, this.rigidTriangles,
                    this.contractSha256, this.bodySha256, this.maskSha256,
                    this.renderedFrames, this.lastEntityId,
                    this.lastBindDelta,
                    reason == null ? "failed" : reason);
        }
    }
}
