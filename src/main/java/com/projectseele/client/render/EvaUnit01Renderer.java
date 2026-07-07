package com.projectseele.client.render;

import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.util.Mth;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven Unit-01. Weapon bones (prog knife, positron cannon) are
 * toggled from the entity's synced weapon state. The world model is hidden
 * from its own first-person camera; EvaCockpitArms supplies a guaranteed
 * camera-space pair of arms instead.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    private boolean pilotView;

    public EvaUnit01Renderer(EntityRendererProvider.Context context)
    {
        super(context, new EvaUnit01GeoModel());
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
        super.render(entity, entityYaw, partialTick, poseStack, bufferSource, packedLight);
    }

    @Override
    public void preRender(PoseStack poseStack, EvaUnit01Entity animatable, BakedGeoModel model,
                          @Nullable MultiBufferSource bufferSource, @Nullable VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender,
                partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        boolean firstPerson = this.pilotView;
        forEachBone(model, bone ->
        {
            bone.setHidden(firstPerson);
            bone.setChildrenHidden(false);
        });
        if (!firstPerson && animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
        {
            // The animation establishes a proper two-hand firing stance;
            // this procedural layer follows the pilot's vertical aim.
            float pitch = -Mth.clamp(animatable.getXRot(), -55.0F, 55.0F) * Mth.DEG_TO_RAD;
            aimArm(model, "arm_r", pitch);
            aimArm(model, "arm_l", pitch * 0.82F);
            aimArm(model, "brazoderecho", pitch);
            aimArm(model, "brazoizquierda", pitch * 0.82F);
        }
        // Weapon visibility applies on top in every view.
        model.getBone("knife").ifPresent(bone ->
                bone.setHidden(bone.isHidden() || animatable.getWeapon() != EvaUnit01Entity.WEAPON_KNIFE));
        model.getBone("cannon").ifPresent(bone ->
                bone.setHidden(bone.isHidden() || animatable.getWeapon() != EvaUnit01Entity.WEAPON_CANNON));
    }

    private static void aimArm(BakedGeoModel model, String name, float pitchRad)
    {
        model.getBone(name).ifPresent(bone -> bone.setRotX(bone.getRotX() + pitchRad));
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
