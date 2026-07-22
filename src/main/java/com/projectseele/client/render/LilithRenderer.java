package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.LilithEntity;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.phys.AABB;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * Static Terminal Dogma renderer. Public resources provide a clean-room
 * fallback; Kiki's reviewed geometry is loaded only from the local test pack.
 */
public final class LilithRenderer extends GeoEntityRenderer<LilithEntity>
{
    private static final ResourceLocation GEOMETRY = resource("geo/lilith.geo.json");
    private static final ResourceLocation FALLBACK_TEXTURE =
            minecraftResource("textures/block/white_concrete.png");
    private static final ResourceLocation ANIMATION =
            resource("animations/lilith.animation.json");
    private static final String[] LAYERS = {
            "lilith_body", "lilith_face_dark", "lilith_mask",
            "lilith_nails", "lilith_spear", "lilith_eyes"
    };
    private static final ResourceLocation PRIMARY_MESH =
            meshResource("lilith_body");

    public LilithRenderer(EntityRendererProvider.Context context)
    {
        super(context, new LocalAddonGeoModel<>(GEOMETRY,
                FALLBACK_TEXTURE, ANIMATION));
        for (String layer : LAYERS)
        {
            ResourceLocation mesh = meshResource(layer);
            ResourceLocation texture =
                    resource("textures/entity/" + layer + ".png");
            this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                    entity -> mesh, entity -> texture));
        }
        this.shadowRadius = 0.0F;
    }

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone,
                                  VertexConsumer buffer, int packedLight,
                                  int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        if (LocalTriangleMeshLayer.hasPart(PRIMARY_MESH, "root"))
        {
            return;
        }
        super.renderCubesOfBone(poseStack, bone, buffer, packedLight,
                packedOverlay, red, green, blue, alpha);
    }

    @Override
    public boolean shouldRender(LilithEntity entity, Frustum frustum,
                                double cameraX, double cameraY,
                                double cameraZ)
    {
        if (super.shouldRender(entity, frustum, cameraX, cameraY, cameraZ))
        {
            return true;
        }
        // The local spear reaches the observation gallery while the crucified
        // wrists span almost the full 48-block containment chamber.
        AABB visualBounds = new AABB(entity.getX() - 23.0D,
                entity.getY() - 1.0D, entity.getZ() - 14.0D,
                entity.getX() + 23.0D, entity.getY() + 35.0D,
                entity.getZ() + 52.0D);
        return frustum.isVisible(visualBounds);
    }

    @Override
    public ResourceLocation getTextureLocation(LilithEntity entity)
    {
        return FALLBACK_TEXTURE;
    }

    public static boolean hasLocalModel()
    {
        return LocalTriangleMeshLayer.hasPart(PRIMARY_MESH, "root");
    }

    private static ResourceLocation meshResource(String layer)
    {
        return resource("mesh/" + layer + ".mesh.json");
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
