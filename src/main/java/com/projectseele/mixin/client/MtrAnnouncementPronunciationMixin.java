package com.projectseele.mixin.client;

import com.projectseele.client.FacilityPronunciationR22;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Pseudo
@Mixin(targets={"com.mojang.text2speech.NarratorWindows","com.mojang.text2speech.NarratorLinux"},remap=false)
public abstract class MtrAnnouncementPronunciationMixin
{
    @ModifyVariable(method="say",at=@At("HEAD"),argsOnly=true,ordinal=0,remap=false)
    private String projectSeele$spokenStationName(String text)
    {
        return FacilityPronunciationR22.spoken(text);
    }
}
