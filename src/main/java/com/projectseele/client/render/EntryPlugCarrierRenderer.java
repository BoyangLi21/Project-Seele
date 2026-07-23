package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EntryPlugCarrierEntity;
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
        this.withScale(2.5F);
        this.shadowRadius = 0.65F;
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
        model.getBone("entry_plug").ifPresent(bone ->
                bone.setRotX((float) Math.toRadians(animatable.getXRot())));
    }

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone,
                                  VertexConsumer buffer, int packedLight,
                                  int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        if ("entry_plug".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(MESH, "entry_plug"))
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
