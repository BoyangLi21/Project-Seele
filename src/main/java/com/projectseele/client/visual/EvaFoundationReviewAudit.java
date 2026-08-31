package com.projectseele.client.visual;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.projectseele.ProjectSeele;
import com.projectseele.client.render.EvaManifoldInnerBody;
import com.projectseele.client.render.EvaUnit01Renderer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;

/** Writes the exact model palette paired with each foundation video frame. */
public final class EvaFoundationReviewAudit
{
    private static long lastSerial;

    private EvaFoundationReviewAudit() {}

    public static boolean record(Minecraft minecraft, int entityId,
                                 String batch, String pose, String view,
                                 int frameNumber) throws Exception
    {
        EvaManifoldInnerBody.FrameSnapshot snapshot =
                EvaManifoldInnerBody.frameSnapshot(entityId);
        if (!snapshot.ready())
        {
            return false;
        }
        if (snapshot.serial() <= lastSerial)
        {
            return false;
        }
        lastSerial = snapshot.serial();
        JsonObject root = new JsonObject();
        root.addProperty("schema", 1);
        root.addProperty("pose", pose);
        root.addProperty("view", view);
        root.addProperty("frame", frameNumber);
        root.addProperty("entityId", entityId);
        root.addProperty("renderSerial", snapshot.serial());
        root.addProperty("triangles", snapshot.triangles());
        root.addProperty("invertedTriangles",
                snapshot.invertedTriangles());
        root.addProperty("collapsedTriangles",
                snapshot.collapsedTriangles());
        root.addProperty("minimumDoubleArea",
                snapshot.minimumDoubleArea());
        root.add("bounds", floats(snapshot.bounds()));
        root.addProperty("orientationCorrectionSweeps",
                snapshot.correctionSweeps());
        root.addProperty("maximumOrientationCorrection",
                snapshot.maximumCorrection());
        JsonArray palette = new JsonArray();
        for (int index = 0; index < snapshot.palette().size(); index++)
        {
            JsonObject bone = new JsonObject();
            bone.addProperty("name", snapshot.palette().get(index));
            bone.add("modelMatrix", floats(
                    snapshot.paletteMatrices().get(index)));
            palette.add(bone);
        }
        root.add("palette", palette);
        JsonArray bones = new JsonArray();
        for (int index = 0; index < snapshot.boneNames().size(); index++)
        {
            JsonObject bone = new JsonObject();
            bone.addProperty("name", snapshot.boneNames().get(index));
            bone.add("modelMatrix", floats(
                    snapshot.boneMatrices().get(index)));
            bones.add(bone);
        }
        root.add("bones", bones);
        EvaManifoldInnerBody.Status status =
                EvaManifoldInnerBody.status();
        root.addProperty("manifoldBodySha256", status.bodySha256());
        root.addProperty("rigidMaskSha256", status.maskSha256());
        root.addProperty("bodyModelTag",
                EvaUnit01Renderer.visualFingerprintForVariant(1).compactTag());
        if (minecraft.level != null
                && minecraft.level.getEntity(entityId)
                instanceof EvaUnit01Entity unit)
        {
            JsonArray position = new JsonArray();
            position.add(unit.getX());
            position.add(unit.getY());
            position.add(unit.getZ());
            root.add("entityPosition", position);
            root.addProperty("weapon", unit.getWeapon());
            root.addProperty("visualPose", unit.getVisualPose());
            root.addProperty("pilotSprinting", unit.isPilotSprinting());
            root.addProperty("visuallyAirborne",
                    unit.isVisuallyAirborneForRender());
            root.addProperty("powerTicks", unit.getPowerTicks());
        }
        Path directory = minecraft.gameDirectory.toPath().resolve(
                "screenshots/projectseele_foundation").resolve(batch);
        Files.createDirectories(directory);
        Files.writeString(directory.resolve("frame_audit.jsonl"),
                root.toString() + "\n", StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND,
                StandardOpenOption.WRITE);
        if (frameNumber == 1)
        {
            ProjectSeele.LOGGER.info(
                    "Foundation audit started: batch={} pose={} view={} "
                            + "palette={} bodyTag={}",
                    batch, pose, view, snapshot.palette().size(),
                    EvaUnit01Renderer.visualFingerprintForVariant(
                            1).compactTag());
        }
        return true;
    }

    private static JsonArray floats(float[] values)
    {
        JsonArray result = new JsonArray();
        for (float value : values)
        {
            result.add(value);
        }
        return result;
    }
}
