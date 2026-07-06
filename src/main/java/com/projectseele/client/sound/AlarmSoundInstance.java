package com.projectseele.client.sound;

import com.projectseele.registry.ModSounds;
import net.minecraft.client.resources.sounds.AbstractTickableSoundInstance;
import net.minecraft.client.resources.sounds.SoundInstance;
import net.minecraft.sounds.SoundSource;

/**
 * The looping air-raid siren. Global (no attenuation): the whole city hears
 * the Angel coming. Stopped externally by {@code ClientAlarmState}.
 */
public class AlarmSoundInstance extends AbstractTickableSoundInstance
{
    public AlarmSoundInstance()
    {
        super(ModSounds.ALARM.get(), SoundSource.HOSTILE, SoundInstance.createUnseededRandom());
        this.looping = true;
        this.delay = 0;
        // Kept well below the action so the siren reads as backdrop, not assault.
        this.volume = 0.45F;
        this.relative = true;
        this.attenuation = SoundInstance.Attenuation.NONE;
        this.x = 0.0D;
        this.y = 0.0D;
        this.z = 0.0D;
    }

    @Override
    public void tick()
    {
        // Nothing to update: global, unattenuated, stopped from outside.
    }
}
