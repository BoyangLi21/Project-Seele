package com.projectseele.client.render;

import java.util.Set;
import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven EVA renderer.
 *
 * GeckoLib is the sole authority for body and arm poses. First person observes
 * this same world-space skeleton from the pilot's head socket. Only mesh
 * shells that physically enclose the camera are suppressed; there is no
 * second arm render pass, reflected scale, camera-space pose or detached
 * viewmodel.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    private static final ResourceLocation MESH_00 =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_unit00.mesh.json");
    private static final ResourceLocation MESH_01 =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_unit01.mesh.json");
    private static final ResourceLocation MESH_02 =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_unit02.mesh.json");
    private static final ResourceLocation POSITRON_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/positron_cannon.mesh.json");
    private static final ResourceLocation POSITRON_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/positron_cannon.png");
    private static final Set<String> CAMERA_COVER_BONES = Set.of(
            "head", "Head", "horn", "Horn", "neck", "Neck");
    private static final Set<String> LOW_STANCE_CAMERA_MESH_COVER = Set.of(
            "torso_lower", "torso_upper");
    private boolean pilotView;
    private boolean strictFailureReported;

    public EvaUnit01Renderer(EntityRendererProvider.Context context)
    {
        super(context, new EvaUnit01GeoModel());
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> meshResourceForVariant(entity.getUnitVariant()), null,
                this::shouldRenderBodyMesh));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> POSITRON_MESH, entity -> POSITRON_TEXTURE));
        this.shadowRadius = 3.6F;
        this.withScale(2.5F);
    }

    @Override
    public void render(EvaUnit01Entity entity, float entityYaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource bufferSource, int packedLight)
    {
        LocalVisualAssetFingerprint.Fingerprint fingerprint =
                visualFingerprintForVariant(entity.getUnitVariant());
        if (LocalVisualAssetFingerprint.isStrictMode() && !fingerprint.valid())
        {
            if (!this.strictFailureReported)
            {
                this.strictFailureReported = true;
                ProjectSeele.LOGGER.error(
                        "Strict high-detail EVA render refused: {}", fingerprint.description());
            }
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        this.pilotView = minecraft.options.getCameraType().isFirstPerson()
                && minecraft.getCameraEntity() != null
                && minecraft.getCameraEntity().getVehicle() == entity;
        super.render(entity, entityYaw, partialTick, poseStack, bufferSource,
                entity.isCrucified() ? LightTexture.FULL_BRIGHT : packedLight);
    }

    @Override
    public boolean shouldRender(EvaUnit01Entity entity, Frustum frustum,
                                double cameraX, double cameraY, double cameraZ)
    {
        Minecraft minecraft = Minecraft.getInstance();
        // The crouch/prone head socket can sit just beyond the entity's coarse
        // gameplay AABB while hands and weapon remain in front of the camera.
        // Do not let frustum culling make the shared body disappear only in
        // first person; every other observer keeps the normal culling path.
        if (minecraft.options.getCameraType().isFirstPerson()
                && minecraft.getCameraEntity() != null
                && minecraft.getCameraEntity().getVehicle() == entity)
        {
            return true;
        }
        return super.shouldRender(entity, frustum, cameraX, cameraY, cameraZ);
    }

    @Override
    public void preRender(PoseStack poseStack, EvaUnit01Entity animatable, BakedGeoModel model,
                          @Nullable MultiBufferSource bufferSource, @Nullable VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender,
                partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        forEachBone(model, bone ->
        {
            bone.setHidden(false);
            bone.setChildrenHidden(false);
        });
        if (this.pilotView)
        {
            forEachBone(model, bone ->
            {
                if (CAMERA_COVER_BONES.contains(bone.getName()))
                {
                    hideSubtree(bone);
                }
            });
        }
        // This is a small additive elevation layer on the one world skeleton,
        // after GeckoLib has evaluated the authored two-hand cannon stance.
        // It is deliberately view-agnostic: first and third person observe the
        // same torso, arms, weapon socket and physical pitch limit.
        if (!isReRender && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            model.getBone("torso_upper").ifPresent(bone -> bone.setRotX(
                    bone.getRotX() + (float) Math.toRadians(animatable.getCannonAimPitch())));
        }
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON);
        setWeaponVisibility(model, "lance", animatable.getWeapon() == EvaUnit01Entity.WEAPON_LANCE);
        boolean shieldBrace = animatable.isShieldBraced()
                || (animatable.getUnitVariant() == EvaUnit01Entity.UNIT_00
                    && animatable.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH);
        setWeaponVisibility(model, "shield", shieldBrace);
        // Insertion is a transient animation but the plug itself stays seated
        // for the entire piloted session, including after the 120-tick startup.
        boolean activating = animatable.getActivationTicks() > 0
                || animatable.isEntryPlugInserted();
        setWeaponVisibility(model, "entry_plug", activating);
        setWeaponVisibility(model, "plug_hatch_l", activating);
        setWeaponVisibility(model, "plug_hatch_r", activating);
    }

    private static void setWeaponVisibility(BakedGeoModel model, String name, boolean active)
    {
        model.getBone(name).ifPresent(bone ->
                bone.setHidden(bone.isHidden() || !active));
    }

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone, VertexConsumer buffer,
                                  int packedLight, int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        EvaUnit01Entity entity = this.getAnimatable();
        boolean bodyMesh = entity != null && LocalTriangleMeshLayer.hasPart(
                meshResourceForVariant(entity.getUnitVariant()), bone.getName());
        boolean cannonMesh = entity != null
                && entity.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                && "cannon".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(POSITRON_MESH, bone.getName());
        if (bodyMesh || cannonMesh)
        {
            return;
        }
        super.renderCubesOfBone(poseStack, bone, buffer, packedLight, packedOverlay,
                red, green, blue, alpha);
    }

    public static ResourceLocation meshResourceForVariant(int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> MESH_00;
            case EvaUnit01Entity.UNIT_02 -> MESH_02;
            default -> MESH_01;
        };
    }

    public static ResourceLocation positronMeshResource()
    {
        return POSITRON_MESH;
    }

    public static LocalVisualAssetFingerprint.Fingerprint visualFingerprintForVariant(int variant)
    {
        return LocalVisualAssetFingerprint.inspect(switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> "eva_unit00";
            case EvaUnit01Entity.UNIT_02 -> "eva_unit02";
            default -> "eva_unit01";
        });
    }

    private boolean shouldRenderBodyMesh(EvaUnit01Entity entity, GeoBone bone)
    {
        if (!this.pilotView)
        {
            return true;
        }
        if (CAMERA_COVER_BONES.contains(bone.getName()))
        {
            return false;
        }
        boolean lowStance = entity.isPilotCrouching() || entity.isPilotProne()
                || entity.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH
                || entity.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE
                || entity.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_CANNON;
        // The low head socket sits inside the chest shell. Suppress only the
        // two enclosing mesh parts, never their bones or descendants: both
        // arms, hands and weapons remain the one evaluated world skeleton.
        return !lowStance || !LOW_STANCE_CAMERA_MESH_COVER.contains(bone.getName());
    }

    private static void hideSubtree(GeoBone bone)
    {
        bone.setHidden(true);
        bone.setChildrenHidden(true);
        for (GeoBone child : bone.getChildBones())
        {
            hideSubtree(child);
        }
    }

    private static void forEachBone(BakedGeoModel model, Consumer<GeoBone> action)
    {
        for (GeoBone bone : model.topLevelBones())
        {
            walkBone(bone, action);
        }
    }

    private static void walkBone(GeoBone bone, Consumer<GeoBone> action)
    {
        action.accept(bone);
        for (GeoBone child : bone.getChildBones())
        {
            walkBone(child, action);
        }
    }
}
