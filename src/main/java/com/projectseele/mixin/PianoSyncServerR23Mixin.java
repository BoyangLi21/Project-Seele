package com.projectseele.mixin;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
/** Host for the version-pinned, dedicated-server-only side stripping. */
@Pseudo
@Mixin(targets="com.solvane.grandpiano.network.PianoSyncPacket",remap=false)
public abstract class PianoSyncServerR23Mixin {}
