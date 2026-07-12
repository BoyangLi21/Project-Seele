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
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven EVA renderer.
 *
 * GeckoLib is the sole authority for body and arm poses. In first person the
 * normal world body remains continuous; only the head shell surrounding the
 * camera is removed. There is no detached screen-space arm viewmodel.
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
            "head", "Head", "Neck", "horn", "pylon_l", "pylon_r");
    private static final Set<String> PRONE_CAMERA_MESH_COVER = Set.of(
            "torso_lower", "torso_upper");
    private boolean pilotView;

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
        Minecraft minecraft = Minecraft.getInstance();
        this.pilotView = minecraft.options.getCameraType().isFirstPerson()
                && minecraft.getCameraEntity() != null
                && minecraft.getCameraEntity().getVehicle() == entity;
        super.render(entity, entityYaw, partialTick, poseStack, bufferSource,
                entity.isCrucified() ? LightTexture.FULL_BRIGHT : packedLight);
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
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON);
        setWeaponVisibility(model, "lance", animatable.getWeapon() == EvaUnit01Entity.WEAPON_LANCE);
        boolean shieldBrace = animatable.isShieldBraced()
                || (animatable.getUnitVariant() == EvaUnit01Entity.UNIT_00
                    && animatable.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH);
        setWeaponVisibility(model, "shield", shieldBrace);
        boolean activating = animatable.getActivationTicks() > 0;
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

    private boolean shouldRenderBodyMesh(EvaUnit01Entity entity, GeoBone bone)
    {
        if (!this.pilotView)
        {
            return true;
        }
        boolean prone = entity.isPilotProne()
                || entity.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE
                || entity.getVisualPose() == EvaUnit01Entity.VISUAL_PRONE_CANNON;
        return !prone || !PRONE_CAMERA_MESH_COVER.contains(bone.getName());
    }

    private static void hideSubtree(GeoBone bone)
    {
        bone.setHidden(true);
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
