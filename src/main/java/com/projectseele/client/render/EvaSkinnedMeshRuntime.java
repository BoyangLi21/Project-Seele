package com.projectseele.client.render;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;

/**
 * Phase-C parser and deterministic CPU reference for weighted EVA meshes.
 *
 * <p>The production Tiger body is intentionally not connected to this class.
 * The reference evaluator establishes the palette, inverse-bind and four-
 * influence contract that a later render layer must reproduce.</p>
 */
public final class EvaSkinnedMeshRuntime
{
    private static final ResourceLocation CONTRACT = new ResourceLocation(
            ProjectSeele.MODID, "eva/eva_skinned_mesh_contract.json");
    private static final ResourceLocation PROBE = new ResourceLocation(
            ProjectSeele.MODID, "eva/skinning_probe_v1.json");
    private static final String FORMAT = "projectseele:skinned_mesh_v1";
    private static final String COORDINATE_SPACE =
            "GECKO_MODEL_SPACE_BLOCKS";
    private static final int STRIDE = 16;
    private static final int MAX_INFLUENCES = 4;
    private static final float WEIGHT_TOLERANCE = 1.0E-5F;
    private static final float PROBE_TOLERANCE = 1.0E-5F;
    private static volatile Status status = Status.missing();

    private EvaSkinnedMeshRuntime() {}

    public static void reload(ResourceManager resources)
    {
        try
        {
            String contractText = read(resources, CONTRACT);
            String probeText = read(resources, PROBE);
            JsonObject contract = JsonParser.parseString(
                    contractText).getAsJsonObject();
            validateContract(contract);
            JsonObject probeJson = JsonParser.parseString(
                    probeText).getAsJsonObject();
            MeshData mesh = parse(probeJson);
            Matrix4f[] probePose = matrices(
                    probeJson.getAsJsonArray("probePoseMatrices"),
                    mesh.palette.size());
            float[] expectedProbe = floats(probeJson.getAsJsonArray(
                    "expectedProbePositions"));
            require(expectedProbe.length == mesh.vertices.size() * 3,
                    "probe expected-position count differs");
            float[] expectedNormals = floats(probeJson.getAsJsonArray(
                    "expectedProbeNormals"));
            require(expectedNormals.length == mesh.vertices.size() * 3,
                    "probe expected-normal count differs");

            Matrix4f[] bindPose = new Matrix4f[mesh.inverseBind.length];
            for (int index = 0; index < bindPose.length; index++)
            {
                bindPose[index] = new Matrix4f(
                        mesh.inverseBind[index]).invert();
            }
            float bindError = maximumPositionError(
                    mesh.bindPositions(), skinPositions(mesh, bindPose));
            float probeError = maximumPositionError(expectedProbe,
                    skinPositions(mesh, probePose));
            float normalError = maximumNormalError(expectedNormals,
                    skinNormals(mesh, probePose));
            if (bindError > PROBE_TOLERANCE
                    || probeError > PROBE_TOLERANCE
                    || normalError > PROBE_TOLERANCE)
            {
                throw new IllegalArgumentException(
                        "skinning probe error exceeds tolerance: bind="
                                + bindError + " pose=" + probeError
                                + " normal=" + normalError);
            }

            status = new Status(true, FORMAT, mesh.palette.size(),
                    mesh.vertices.size(), mesh.indices.length / 3,
                    mesh.blendedVertices, bindError, probeError,
                    normalError, sha256(contractText), sha256(probeText),
                    false);
            ProjectSeele.LOGGER.info(
                    "EVA skinned-mesh runtime probe passed: format={} palette={} "
                            + "vertices={} triangles={} blended={} bindDelta={} "
                            + "poseDelta={} normalDelta={} liveBody=false",
                    FORMAT, mesh.palette.size(), mesh.vertices.size(),
                    mesh.indices.length / 3, mesh.blendedVertices,
                    bindError, probeError, normalError);
        }
        catch (Exception exception)
        {
            status = Status.failed(exception.getMessage());
            ProjectSeele.LOGGER.error(
                    "EVA skinned-mesh runtime probe rejected", exception);
        }
    }

    public static Status status()
    {
        return status;
    }

    /** Loads any mesh that conforms to the reusable Phase-C v1 contract. */
    public static MeshData load(ResourceManager resources,
                                ResourceLocation location) throws Exception
    {
        return parse(JsonParser.parseString(
                read(resources, location)).getAsJsonObject());
    }

    private static void validateContract(JsonObject contract)
    {
        require(contract.get("schema").getAsInt() == 1,
                "unsupported skinning contract schema");
        require("C".equals(contract.get("phase").getAsString()),
                "skinning contract is not Phase C");
        require(FORMAT.equals(contract.get("format").getAsString()),
                "skinning contract format differs");
        require(COORDINATE_SPACE.equals(
                contract.get("coordinateSpace").getAsString()),
                "skinning coordinate space differs");
        require(contract.get("stride").getAsInt() == STRIDE,
                "skinning contract stride differs");
        require(contract.get("maxInfluences").getAsInt()
                == MAX_INFLUENCES, "skinning influence limit differs");
        require(Math.abs(contract.get("weightSumTolerance").getAsFloat()
                - WEIGHT_TOLERANCE) <= 1.0E-9F,
                "skinning weight tolerance differs");
        require((ProjectSeele.MODID + ":eva/skinning_probe_v1.json").equals(
                contract.get("probeResource").getAsString()),
                "skinning probe resource differs");
        JsonObject activation = contract.getAsJsonObject(
                "runtimeActivation");
        require(!activation.get("skinnedBodyEnabled").getAsBoolean()
                && !activation.get("productionAssetPresent").getAsBoolean()
                && activation.get(
                "humanReviewRequiredBeforeActivation").getAsBoolean(),
                "Phase-C probe escaped research isolation");
    }

    private static MeshData parse(JsonObject root)
    {
        require(root.get("schema").getAsInt() == 1,
                "unsupported skinned mesh schema");
        require(FORMAT.equals(root.get("format").getAsString()),
                "unsupported skinned mesh format");
        require(COORDINATE_SPACE.equals(
                root.get("coordinateSpace").getAsString()),
                "unsupported skinned mesh coordinate space");
        require(root.get("stride").getAsInt() == STRIDE,
                "unsupported skinned mesh stride");
        require(root.get("maxInfluences").getAsInt()
                == MAX_INFLUENCES, "unsupported influence count");

        List<String> palette = new ArrayList<>();
        Set<String> unique = new HashSet<>();
        for (JsonElement element : root.getAsJsonArray("palette"))
        {
            String name = element.getAsString();
            require(!name.isBlank() && unique.add(name),
                    "blank or duplicate palette bone");
            palette.add(name);
        }
        require(!palette.isEmpty(), "empty skinning palette");
        Matrix4f[] inverseBind = matrices(
                root.getAsJsonArray("inverseBindMatrices"), palette.size());

        JsonArray packed = root.getAsJsonArray("vertices");
        require(packed.size() > 0 && packed.size() % STRIDE == 0,
                "incomplete skinned vertex buffer");
        List<VertexData> vertices = new ArrayList<>();
        int blendedVertices = 0;
        for (int base = 0; base < packed.size(); base += STRIDE)
        {
            float[] values = new float[STRIDE];
            for (int offset = 0; offset < STRIDE; offset++)
            {
                values[offset] = packed.get(base + offset).getAsFloat();
                require(Float.isFinite(values[offset]),
                        "non-finite packed vertex value");
            }
            Vector3f position = new Vector3f(
                    values[0], values[1], values[2]);
            Vector3f normal = new Vector3f(
                    values[5], values[6], values[7]);
            require(normal.lengthSquared() > 1.0E-10F,
                    "zero-length bind normal");
            normal.normalize();
            int[] joints = new int[MAX_INFLUENCES];
            float[] weights = new float[MAX_INFLUENCES];
            float weightSum = 0.0F;
            int positive = 0;
            for (int influence = 0; influence < MAX_INFLUENCES;
                    influence++)
            {
                float rawJoint = values[8 + influence];
                int joint = Math.round(rawJoint);
                require(Math.abs(rawJoint - joint) <= WEIGHT_TOLERANCE
                        && joint >= 0 && joint < palette.size(),
                        "invalid palette index");
                float weight = values[12 + influence];
                require(weight >= 0.0F && weight <= 1.0F,
                        "invalid skin weight");
                joints[influence] = joint;
                weights[influence] = weight;
                weightSum += weight;
                if (weight > WEIGHT_TOLERANCE) positive++;
            }
            require(Math.abs(weightSum - 1.0F) <= WEIGHT_TOLERANCE,
                    "skin weights do not sum to one");
            require(positive > 0, "vertex has no positive influence");
            if (positive > 1) blendedVertices++;
            vertices.add(new VertexData(position, values[3], values[4],
                    normal, joints, weights));
        }
        require(blendedVertices > 0,
                "probe has no genuinely blended vertex");

        JsonArray rawIndices = root.getAsJsonArray("indices");
        require(rawIndices.size() > 0 && rawIndices.size() % 3 == 0,
                "incomplete skin triangle buffer");
        int[] indices = new int[rawIndices.size()];
        for (int index = 0; index < indices.length; index++)
        {
            indices[index] = rawIndices.get(index).getAsInt();
            require(indices[index] >= 0
                    && indices[index] < vertices.size(),
                    "skin triangle index out of range");
        }
        for (int index = 0; index < indices.length; index += 3)
        {
            int a = indices[index];
            int b = indices[index + 1];
            int c = indices[index + 2];
            require(a != b && b != c && a != c,
                    "skin triangle repeats a vertex");
            Vector3f edgeA = new Vector3f(
                    vertices.get(b).position).sub(vertices.get(a).position);
            Vector3f edgeB = new Vector3f(
                    vertices.get(c).position).sub(vertices.get(a).position);
            require(edgeA.cross(edgeB).lengthSquared() > 1.0E-12F,
                    "degenerate skin triangle");
        }
        return new MeshData(List.copyOf(palette), inverseBind,
                List.copyOf(vertices), indices, blendedVertices);
    }

    private static Matrix4f[] matrices(JsonArray source, int count)
    {
        require(source.size() == count, "matrix palette size differs");
        Matrix4f[] result = new Matrix4f[count];
        for (int index = 0; index < count; index++)
        {
            float[] values = floats(source.get(index).getAsJsonArray());
            require(values.length == 16, "palette matrix is not 4x4");
            Matrix4f matrix = new Matrix4f().set(values);
            require(Float.isFinite(matrix.determinant())
                    && Math.abs(matrix.determinant()) > 1.0E-8F,
                    "singular palette matrix");
            result[index] = matrix;
        }
        return result;
    }

    public static float[] skinPositions(MeshData mesh,
                                        Matrix4f[] currentPose)
    {
        Matrix4f[] skinMatrices = skinMatrices(mesh, currentPose);
        float[] result = new float[mesh.vertices.size() * 3];
        for (int index = 0; index < mesh.vertices.size(); index++)
        {
            VertexData vertex = mesh.vertices.get(index);
            Vector3f total = new Vector3f();
            for (int influence = 0; influence < MAX_INFLUENCES;
                    influence++)
            {
                float weight = vertex.weights[influence];
                if (weight <= 0.0F) continue;
                Vector3f transformed = skinMatrices[
                        vertex.joints[influence]].transformPosition(
                        new Vector3f(vertex.position));
                total.fma(weight, transformed);
            }
            result[index * 3] = total.x;
            result[index * 3 + 1] = total.y;
            result[index * 3 + 2] = total.z;
        }
        return result;
    }

    public static Vector3f[] skinNormals(MeshData mesh,
                                         Matrix4f[] currentPose)
    {
        Matrix4f[] skinMatrices = skinMatrices(mesh, currentPose);
        Matrix3f[] normalMatrices = new Matrix3f[skinMatrices.length];
        for (int index = 0; index < skinMatrices.length; index++)
        {
            normalMatrices[index] = new Matrix3f(
                    skinMatrices[index]).invert().transpose();
        }
        Vector3f[] result = new Vector3f[mesh.vertices.size()];
        for (int index = 0; index < mesh.vertices.size(); index++)
        {
            VertexData vertex = mesh.vertices.get(index);
            Vector3f total = new Vector3f();
            for (int influence = 0; influence < MAX_INFLUENCES;
                    influence++)
            {
                float weight = vertex.weights[influence];
                if (weight <= 0.0F) continue;
                Vector3f transformed = normalMatrices[
                        vertex.joints[influence]].transform(
                        new Vector3f(vertex.normal));
                total.fma(weight, transformed);
            }
            require(total.lengthSquared() > 1.0E-10F,
                    "skinned normal collapsed");
            result[index] = total.normalize();
        }
        return result;
    }

    private static Matrix4f[] skinMatrices(MeshData mesh,
                                           Matrix4f[] currentPose)
    {
        require(currentPose.length == mesh.inverseBind.length,
                "current pose palette size differs");
        Matrix4f[] result = new Matrix4f[currentPose.length];
        for (int index = 0; index < result.length; index++)
        {
            float determinant = currentPose[index].determinant();
            require(Float.isFinite(determinant)
                    && Math.abs(determinant) > 1.0E-8F,
                    "singular current-pose matrix");
            result[index] = new Matrix4f(currentPose[index]).mul(
                    mesh.inverseBind[index]);
        }
        return result;
    }

    private static float maximumPositionError(float[] expected,
                                              float[] actual)
    {
        require(expected.length == actual.length,
                "position buffers differ in length");
        float result = 0.0F;
        for (int index = 0; index < expected.length; index++)
        {
            result = Math.max(result, Math.abs(
                    expected[index] - actual[index]));
        }
        return result;
    }

    private static float maximumNormalError(float[] expected,
                                            Vector3f[] actual)
    {
        require(expected.length == actual.length * 3,
                "normal buffers differ in length");
        float result = 0.0F;
        for (int index = 0; index < actual.length; index++)
        {
            Vector3f normal = actual[index];
            result = Math.max(result, Math.abs(normal.length() - 1.0F));
            result = Math.max(result, Math.abs(
                    normal.x - expected[index * 3]));
            result = Math.max(result, Math.abs(
                    normal.y - expected[index * 3 + 1]));
            result = Math.max(result, Math.abs(
                    normal.z - expected[index * 3 + 2]));
        }
        return result;
    }

    private static float[] floats(JsonArray source)
    {
        float[] result = new float[source.size()];
        for (int index = 0; index < result.length; index++)
        {
            result[index] = source.get(index).getAsFloat();
            require(Float.isFinite(result[index]), "non-finite float value");
        }
        return result;
    }

    private static String read(ResourceManager resources,
                               ResourceLocation location) throws Exception
    {
        try (InputStream stream = resources.getResource(location)
                .orElseThrow(() -> new IllegalStateException(
                        "missing EVA skinning resource " + location)).open())
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

    public record VertexData(Vector3f position, float u, float v,
                             Vector3f normal, int[] joints,
                             float[] weights) {}

    public record MeshData(List<String> palette,
                           Matrix4f[] inverseBind,
                           List<VertexData> vertices, int[] indices,
                           int blendedVertices)
    {
        private float[] bindPositions()
        {
            float[] result = new float[this.vertices.size() * 3];
            for (int index = 0; index < this.vertices.size(); index++)
            {
                Vector3f position = this.vertices.get(index).position;
                result[index * 3] = position.x;
                result[index * 3 + 1] = position.y;
                result[index * 3 + 2] = position.z;
            }
            return result;
        }
    }

    public record Status(boolean ready, String format, int paletteBones,
                         int vertices, int triangles,
                         int blendedVertices, float bindError,
                         float probeError, float normalError,
                         String contractSha256, String probeSha256,
                         boolean liveBodyEnabled)
    {
        private static Status missing()
        {
            return failed("not_loaded");
        }

        private static Status failed(String reason)
        {
            return new Status(false, reason == null ? "failed" : reason,
                    0, 0, 0, 0, Float.NaN, Float.NaN, Float.NaN,
                    "missing", "missing", false);
        }
    }
}
