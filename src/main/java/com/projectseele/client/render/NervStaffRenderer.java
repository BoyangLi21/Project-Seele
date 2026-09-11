package com.projectseele.client.render;

import com.projectseele.entity.NervStaffEntity;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelLayers;
import net.minecraft.client.renderer.entity.*;
import net.minecraft.resources.ResourceLocation;
import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.renderer.MultiBufferSource;

public final class NervStaffRenderer extends MobRenderer<NervStaffEntity,PlayerModel<NervStaffEntity>>
{
    private static final class StaffModel extends PlayerModel<NervStaffEntity>
    {
        StaffModel(net.minecraft.client.model.geom.ModelPart root,boolean slim){super(root,slim);}
        @Override public void setupAnim(NervStaffEntity entity,float swing,float amount,float time,float yaw,float pitch)
        {
            super.setupAnim(entity,swing,amount,time,yaw,pitch);
            if(entity.activity()==2){rightArm.xRot=-1.25F;rightArm.yRot=-.15F;rightSleeve.copyFrom(rightArm);}
        }
    }
    private final PlayerModel<NervStaffEntity> slim,regular;
    public NervStaffRenderer(EntityRendererProvider.Context context)
    {
        super(context,new StaffModel(context.bakeLayer(ModelLayers.PLAYER),false),.35F);regular=model;slim=new StaffModel(context.bakeLayer(ModelLayers.PLAYER_SLIM),true);
    }
    @Override public ResourceLocation getTextureLocation(NervStaffEntity entity){return NervStaffSkins.forStaff(entity).texture();}
    @Override public void render(NervStaffEntity entity,float yaw,float partial,PoseStack pose,MultiBufferSource buffers,int light)
    {
        model=NervStaffSkins.forStaff(entity).slim()?slim:regular;super.render(entity,yaw,partial,pose,buffers,light);
    }
    @Override protected boolean shouldShowName(NervStaffEntity entity){return super.shouldShowName(entity)&&entity.distanceToSqr(net.minecraft.client.Minecraft.getInstance().player)<144;}
}
