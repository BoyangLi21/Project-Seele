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
            hat.visible=!java.util.Set.of("misato","ritsuko","maya","fuyutsuki").contains(entity.skin());
            float reach=entity.pressBlend(time-entity.tickCount);
            if(reach>0)
            {
                var target=net.minecraft.world.phys.Vec3.atCenterOf(entity.pressTarget());
                var state=entity.level().getBlockState(entity.pressTarget());
                var facing=net.minecraft.world.level.block.state.properties.BlockStateProperties.HORIZONTAL_FACING;
                if(state.hasProperty(facing))target=target.add(net.minecraft.world.phys.Vec3.atLowerCornerOf(state.getValue(facing).getNormal()).scale(.38));
                boolean low=target.y-entity.getY()<1;
                if(low)
                {
                    body.xRot+=.45F*reach;body.y+=3.2F*reach;head.y+=4.2F*reach;
                    rightArm.y+=3.2F*reach;leftArm.y+=3.2F*reach;rightArm.z-=2.4F*reach;leftArm.z-=2.4F*reach;
                    rightLeg.z+=4*reach;leftLeg.z+=4*reach;rightLeg.y+=.2F*reach;leftLeg.y+=.2F*reach;
                }
                double angle=Math.toRadians(entity.yBodyRot);
                var forward=new net.minecraft.world.phys.Vec3(-Math.sin(angle),0,Math.cos(angle));
                var right=new net.minecraft.world.phys.Vec3(-Math.cos(angle),0,-Math.sin(angle));
                var shoulder=entity.position().add(right.scale(.3125)).add(forward.scale(low?.15:0)).add(0,low?1.175:1.375,0);
                var delta=target.subtract(shoulder);double ahead=delta.dot(forward),side=delta.dot(right);
                float pitchTarget=(float)-Math.atan2(Math.hypot(ahead,side),-delta.y);
                rightArm.xRot=net.minecraft.util.Mth.lerp(reach,rightArm.xRot,net.minecraft.util.Mth.clamp(pitchTarget,-2.6F,-.1F));
                rightArm.yRot=net.minecraft.util.Mth.lerp(reach,rightArm.yRot,(float)Math.atan2(side,Math.max(.01,ahead)));
                rightSleeve.copyFrom(rightArm);leftSleeve.copyFrom(leftArm);jacket.copyFrom(body);
                rightPants.copyFrom(rightLeg);leftPants.copyFrom(leftLeg);hat.copyFrom(head);
            }
        }
    }
    private final PlayerModel<NervStaffEntity> slim,regular;
    public NervStaffRenderer(EntityRendererProvider.Context context)
    {
        super(context,new StaffModel(context.bakeLayer(ModelLayers.PLAYER),false),.35F);regular=model;slim=new StaffModel(context.bakeLayer(ModelLayers.PLAYER_SLIM),true);
        addLayer(new NervStaffAccessoryLayer(this));
    }
    @Override public ResourceLocation getTextureLocation(NervStaffEntity entity){return NervStaffSkins.forStaff(entity).texture();}
    @Override public void render(NervStaffEntity entity,float yaw,float partial,PoseStack pose,MultiBufferSource buffers,int light)
    {
        model=NervStaffSkins.forStaff(entity).slim()?slim:regular;super.render(entity,yaw,partial,pose,buffers,light);
    }
    @Override protected boolean shouldShowName(NervStaffEntity entity){return super.shouldShowName(entity)&&entity.distanceToSqr(net.minecraft.client.Minecraft.getInstance().player)<144;}
}
