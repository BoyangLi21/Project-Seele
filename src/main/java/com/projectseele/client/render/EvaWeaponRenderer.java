package com.projectseele.client.render;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaScale;
import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.entity.EvaWeaponEntity;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.entity.EntityRenderer;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.inventory.InventoryMenu;

/** Detailed local-pack armament while it is locked to a physical lift. */
public final class EvaWeaponRenderer extends EntityRenderer<EvaWeaponEntity>
{
    public EvaWeaponRenderer(EntityRendererProvider.Context context)
    {
        super(context);
        this.shadowRadius = 0.8F;
    }

    @Override
    public void render(EvaWeaponEntity entity, float yaw, float partialTick,
                       PoseStack poses, MultiBufferSource buffers,
                       int packedLight)
    {
        if (!entity.isPayloadVisible())
        {
            return;
        }
        ResourceLocation mesh = mesh(entity.getWeapon());
        ResourceLocation texture = texture(entity.getWeapon());
        if (mesh == null || texture == null)
        {
            return;
        }
        poses.pushPose();
        poses.mulPose(Axis.YP.rotationDegrees(180.0F - yaw));
        poses.scale(EvaScale.RENDER_SCALE, EvaScale.RENDER_SCALE,
                EvaScale.RENDER_SCALE);
        LocalTriangleMeshLayer.renderStandalone(poses, buffers, mesh, texture,
                packedLight, OverlayTexture.NO_OVERLAY);
        poses.popPose();
        super.render(entity, yaw, partialTick, poses, buffers, packedLight);
    }

    private static ResourceLocation mesh(int weapon)
    {
        String name = switch (weapon)
        {
            case EvaUnit01Entity.WEAPON_KNIFE -> "progressive_knife";
            case EvaUnit01Entity.WEAPON_CANNON -> "positron_cannon";
            case EvaUnit01Entity.WEAPON_LANCE -> "longinus_lance";
            case EvaUnit01Entity.WEAPON_RIFLE -> "eva_pallet_smg";
            case EvaUnit01Entity.WEAPON_N2 -> "eva_n2_device";
            default -> null;
        };
        return name == null ? null : new ResourceLocation(
                ProjectSeele.MODID, "mesh/" + name + ".mesh.json");
    }

    private static ResourceLocation texture(int weapon)
    {
        String name = switch (weapon)
        {
            case EvaUnit01Entity.WEAPON_KNIFE -> "progressive_knife";
            case EvaUnit01Entity.WEAPON_CANNON -> "positron_cannon";
            case EvaUnit01Entity.WEAPON_LANCE -> "longinus_lance";
            case EvaUnit01Entity.WEAPON_RIFLE -> "eva_pallet_smg";
            case EvaUnit01Entity.WEAPON_N2 -> "eva_n2_device";
            default -> null;
        };
        return name == null ? null : new ResourceLocation(
                ProjectSeele.MODID, "textures/entity/" + name + ".png");
    }

    @Override
    public ResourceLocation getTextureLocation(EvaWeaponEntity entity)
    {
        return InventoryMenu.BLOCK_ATLAS;
    }
}
