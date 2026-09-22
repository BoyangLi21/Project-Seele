package com.projectseele.entity;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.projectseele.ProjectSeele;
import com.projectseele.registry.ModSounds;
import net.minecraft.core.BlockPos;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.Vec3;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.WeakHashMap;

/** Foot contacts use the same server gait phase as the rendered body. */
public final class EvaMovementSounds
{
    private static final Map<EvaUnit01Entity,Float> PREVIOUS=new WeakHashMap<>();
    private static final JsonObject CONTACTS=load();
    private static JsonObject load()
    {
        try(var in=EvaMovementSounds.class.getResourceAsStream("/assets/projectseele/motion/eva_gait_contacts_r10.json"))
        {
            if(in==null)throw new IllegalStateException("Missing gait sound contacts");
            return JsonParser.parseReader(new InputStreamReader(in,StandardCharsets.UTF_8)).getAsJsonObject().getAsJsonObject("contacts");
        }
        catch(Exception e){ProjectSeele.LOGGER.error("EVA gait sound contacts rejected",e);return new JsonObject();}
    }
    private static float contact(String clip,String side,boolean backwards)
    {
        if(!CONTACTS.has(clip))return side.equals("l")?.7F:.2F;
        var rows=CONTACTS.getAsJsonObject(clip).getAsJsonObject(side).getAsJsonArray(backwards?"reverse":"forward");
        return rows.isEmpty()?(side.equals("l")?.7F:.2F):rows.get(0).getAsFloat();
    }
    public static void tick(EvaUnit01Entity eva,boolean moving)
    {
        if(eva.level().isClientSide)return;
        float phase=eva.rifleGaitPhase(1);Float previous=PREVIOUS.put(eva,phase);
        if(previous==null||!moving||!eva.onGround()||!eva.isPoweredOn()||eva.isNervLogisticsLocked()||eva.isPilotProne()||eva.isSilent())return;
        float delta=phase-previous;if(delta>.5F)delta-=1;if(delta<-.5F)delta+=1;
        if(Math.abs(delta)<1e-5F||Math.abs(delta)>.3F)return;
        boolean backwards=delta<0;float run=eva.rifleRunBlend(1);
        for(String side:new String[]{"l","r"})
        {
            float threshold=eva.isPilotCrouching()?contact("crouch_walk",side,backwards):Mth.lerp(run,contact("walk",side,backwards),contact("run",side,backwards));
            float before=Mth.positiveModulo(previous-threshold,1),after=Mth.positiveModulo(phase-threshold,1);
            if(backwards?after<=before:after>=before)continue;
            Vec3 forward=eva.getForward().multiply(1,0,1).normalize(),lateral=new Vec3(forward.z,0,-forward.x);
            Vec3 foot=eva.position().add(lateral.scale((side.equals("l")?1:-1)*eva.getBbWidth()*.24)).add(forward.scale(backwards?-2:3));
            var state=eva.level().getBlockState(BlockPos.containing(foot.x,foot.y-.2,foot.z));
            boolean soil=state.is(BlockTags.DIRT)||state.is(BlockTags.SAND)||state.is(BlockTags.LEAVES);
            play(eva,foot,soil?ModSounds.EVA_FOOT_SOIL.get():ModSounds.EVA_FOOT_CONCRETE.get(),eva.isPilotCrouching()?1.25F:2.6F+.7F*run,.86F+eva.getRandom().nextFloat()*.06F);
            if(eva.getTags().contains("seele_motion_lab"))ProjectSeele.LOGGER.info("EVA FOOT CONTACT side={} phase={} position={} material={}",side,phase,foot,state);
        }
    }
    public static void swing(EvaUnit01Entity eva,float volume)
    {
        play(eva,eva.position().add(0,eva.getBbHeight()*.62,0).add(eva.getForward().scale(10)),ModSounds.EVA_SWING.get(),volume,1);
    }
    public static void play(EvaUnit01Entity eva,Vec3 point,SoundEvent sound,float volume,float pitch)
    {
        if(!eva.level().isClientSide&&!eva.isSilent())eva.level().playSound(null,point.x,point.y,point.z,SoundEvent.createFixedRangeEvent(sound.getLocation(),384F),SoundSource.PLAYERS,volume,pitch);
    }
}
