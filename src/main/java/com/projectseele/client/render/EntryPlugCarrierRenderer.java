package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EntryPlugCarrierEntity;
import com.projectseele.entity.EvaScale;
import com.projectseele.world.EntryPlugKinematics;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/** Renders the reviewed local entry-plug mesh as an independent carrier. */
public final class EntryPlugCarrierRenderer
        extends GeoEntityRenderer<EntryPlugCarrierEntity>
{
    private static final ResourceLocation GEOMETRY =
            resource("geo/entry_plug_carrier.geo.json");
    private static final ResourceLocation ANIMATION =
            resource("animations/entry_plug_carrier.animation.json");
    private static final ResourceLocation MESH =
            resource("mesh/entry_plug.mesh.json");
    private static final ResourceLocation LOCAL_TEXTURE =
            resource("textures/entity/entry_plug.png");
    private static final ResourceLocation FALLBACK_TEXTURE =
            minecraftResource("textures/block/white_concrete.png");
    public EntryPlugCarrierRenderer(EntityRendererProvider.Context context)
    {
        super(context, new LocalAddonGeoModel<>(GEOMETRY,
                FALLBACK_TEXTURE, ANIMATION));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> MESH, entity -> LOCAL_TEXTURE));
        this.withScale(EvaScale.ENTRY_PLUG_RENDER_SCALE);
        this.shadowRadius = 1.0F;
    }

    @Override
    public void render(EntryPlugCarrierEntity animatable, float entityYaw,
                       float partialTick, PoseStack poseStack,
                       MultiBufferSource bufferSource, int packedLight)
    {
        // The persistent carrier still exists and holds the pilot while seated,
        // but the external shell is physically inside the airframe.
        if (!animatable.isShellVisible())
        {
            return;
        }
        super.render(animatable, entityYaw, partialTick, poseStack,
                bufferSource, packedLight);
    }

    @Override
    protected void applyRotations(EntryPlugCarrierEntity animatable,
                                  PoseStack poseStack, float ageInTicks,
                                  float rotationYaw, float partialTick)
    {
        if (!animatable.hasCanonicalPose())
        {
            super.applyRotations(animatable, poseStack, ageInTicks,
                    rotationYaw, partialTick);
            return;
        }
        poseStack.mulPose(animatable.getCanonicalRotation(partialTick));
    }

    @Override
    public void preRender(PoseStack poseStack,
                          EntryPlugCarrierEntity animatable,
                          BakedGeoModel model,
                          net.minecraft.client.renderer.MultiBufferSource bufferSource,
                          VertexConsumer buffer, boolean isReRender,
                          float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, animatable, model, bufferSource, buffer,
                isReRender, partialTick, packedLight, packedOverlay,
                red, green, blue, alpha);
        float hatch = animatable.getHatchOpenAmount();
        model.getBone("plug_hatch_l").ifPresent(bone ->
        {
            bone.setPosX(-EntryPlugKinematics.HATCH_OPEN_TRAVEL_MODEL * hatch);
            bone.setRotZ(0.0F);
        });
        model.getBone("plug_hatch_r").ifPresent(bone ->
        {
            bone.setPosX(EntryPlugKinematics.HATCH_OPEN_TRAVEL_MODEL * hatch);
            bone.setRotZ(0.0F);
        });
    }

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone,
                                  VertexConsumer buffer, int packedLight,
                                  int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        if (LocalTriangleMeshLayer.hasPart(MESH, bone.getName()))
        {
            return;
        }
        super.renderCubesOfBone(poseStack, bone, buffer, packedLight,
                packedOverlay, red, green, blue, alpha);
    }

    @Override
    public ResourceLocation getTextureLocation(EntryPlugCarrierEntity entity)
    {
        return FALLBACK_TEXTURE;
    }

    @SuppressWarnings("removal")
    private static ResourceLocation resource(String path)
    {
        return new ResourceLocation(ProjectSeele.MODID, path);
    }

    @SuppressWarnings("removal")
    private static ResourceLocation minecraftResource(String path)
    {
        return new ResourceLocation("minecraft", path);
    }
}
