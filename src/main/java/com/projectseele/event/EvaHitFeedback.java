package com.projectseele.event;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.*;
import com.projectseele.network.*;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.event.entity.living.LivingDamageEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;

/** Real accepted damage supplies contact position and direction; shield strikes remain shield feedback. */
@Mod.EventBusSubscriber(modid=ProjectSeele.MODID)
public final class EvaHitFeedback
{
    private record Contact(LivingEntity target,Vec3 point,Vec3 direction) {}
    private static final ThreadLocal<Contact> CONTACT=new ThreadLocal<>();
    public static boolean hurt(LivingEntity target,DamageSource source,float amount,Vec3 point,Vec3 direction)
    {
        Contact old=CONTACT.get();CONTACT.set(new Contact(target,point,direction));try{return target.hurt(source,amount);}finally{if(old==null)CONTACT.remove();else CONTACT.set(old);}
    }
    @SubscribeEvent public static void damaged(LivingDamageEvent event)
    {
        LivingEntity target=event.getEntity();if(!(target.level() instanceof ServerLevel level)||!(target instanceof EvaUnit01Entity||target instanceof Angel)||event.getAmount()<=0)return;
        var c=CONTACT.get();Vec3 origin=event.getSource().getSourcePosition();if(origin==null)origin=target.position().subtract(target.getLookAngle());
        Vec3 point=c!=null&&c.target==target?c.point:target.position().add(0,target.getBbHeight()*.58,0);
        Vec3 direction=c!=null&&c.target==target?c.direction:target.position().subtract(origin).normalize();
        float strength=(float)Math.min(1.2,.22+Math.sqrt(event.getAmount()/Math.max(1,target.getMaxHealth()))*2.0);
        float height=(float)Math.max(0,Math.min(1,(point.y-target.getY())/target.getBbHeight()));long tick=level.getGameTime();EvaImpactResponse.add(target,tick,direction,strength,height);
        SeeleNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(()->target),new ClientboundImpactResponsePacket(target.getId(),tick,direction,strength,height));
        level.sendParticles(target instanceof EvaUnit01Entity?ParticleTypes.ELECTRIC_SPARK:ParticleTypes.DAMAGE_INDICATOR,point.x,point.y,point.z,8,.55,.55,.55,.07);
        level.sendParticles(ParticleTypes.POOF,point.x,point.y,point.z,5,.45,.45,.45,.04);
    }
    private EvaHitFeedback() {}
}
