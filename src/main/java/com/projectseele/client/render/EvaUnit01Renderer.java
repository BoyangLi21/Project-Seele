package com.projectseele.client.render;

import java.util.Set;
import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
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
    private static final Set<String> CAMERA_COVER_BONES = Set.of(
            "head", "Head", "Neck", "horn");
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
