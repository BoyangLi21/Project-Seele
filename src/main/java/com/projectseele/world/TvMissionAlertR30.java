package com.projectseele.world;

import com.google.gson.JsonParser;
import com.projectseele.registry.ModBlocks;
import com.projectseele.registry.ModSounds;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.*;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.storage.LevelResource;
import java.nio.file.Files;
import java.util.*;

/** A short, persistent detection/identification briefing precedes every selected sortie. */
public final class TvMissionAlertR30
{
    private static final Map<ServerLevel,List<BlockPos>> BEACONS=new WeakHashMap<>();
    private static final Map<ServerLevel,Long> LAST_LINE=new WeakHashMap<>();
    public static boolean active(ServerLevel level){return TvCampaignSavedData.get(level).phase.equals("alert");}
    private static List<BlockPos> beacons(ServerLevel level)
    {
        return BEACONS.computeIfAbsent(level,l->{
            var path=l.getServer().getWorldPath(LevelResource.ROOT).resolve("mission_alert_r30.json");if(!Files.isRegularFile(path))return List.of();
            try{var out=new ArrayList<BlockPos>();for(var raw:JsonParser.parseString(Files.readString(path)).getAsJsonObject().getAsJsonArray("command_beacons")){var a=raw.getAsJsonArray();out.add(new BlockPos(a.get(0).getAsInt(),a.get(1).getAsInt(),a.get(2).getAsInt()));}return List.copyOf(out);}
            catch(Exception e){throw new IllegalStateException("Invalid mission alarm circuit",e);}
        });
    }
    public static boolean tick(ServerLevel level,TvCampaignSavedData data,ServerPlayer commander)
    {
        long age=level.getGameTime()-data.alertStarted;
        for(var p:beacons(level))if(level.hasChunkAt(p))
        {var s=level.getBlockState(p);boolean lit=age<180&&age%20<10;if(s.is(ModBlocks.NERV_ALERT_LIGHT.get())&&s.getValue(BlockStateProperties.LIT)!=lit)level.setBlock(p,s.setValue(BlockStateProperties.LIT,lit),2);}
        if(age<180&&age%60==0)
        {
            for(BlockPos p:List.of(new BlockPos(30,-412,289),new BlockPos(30,-391,-240)))
                level.playSound(null,p,ModSounds.FACILITY.get("facility_siren").get(),SoundSource.BLOCKS,.6F,1);
        }
        Long lastLine=LAST_LINE.get(level);
        if(commander!=null&&data.alertLine<5&&age>=data.alertLine*35L
                &&(data.alertLine==0||lastLine==null||level.getGameTime()<lastLine||level.getGameTime()-lastLine>=35))
        {
            String[][] lines={{"伊吹摩耶","监视网捕捉到异常反应。正在比对波形。"},{"伊吹摩耶","波形确认为蓝色。目标是使徒。"},{"葛城美里","司令，迎击命令已收到。各部门进入第一种战斗配置。"},{"赤木律子","机体检查开始。确认驾驶员连接以后，再解除发射联锁。"},{"葛城美里","前线交给我协调。请确认中央城区已完成收纳，保持撤回通道畅通。"}};
            int index=data.alertLine++;var line=lines[index];NervStaffDialogue.say(commander,line[0]+" · 指挥通信",line[1]);
            if(index<3)commander.playNotifySound(ModSounds.FACILITY.get(new String[]{"pa_signal_r30","pa_blue_r30","pa_alert_r30"}[index]).get(),SoundSource.VOICE,.9F,1);
            LAST_LINE.put(level,level.getGameTime());data.setDirty();
        }
        return age>=180&&data.alertLine>=5;
    }
    public static void clear(ServerLevel level)
    {for(var p:beacons(level))if(level.hasChunkAt(p)){var s=level.getBlockState(p);if(s.is(ModBlocks.NERV_ALERT_LIGHT.get()))level.setBlock(p,s.setValue(BlockStateProperties.LIT,false),2);}}
    private TvMissionAlertR30(){}
}
