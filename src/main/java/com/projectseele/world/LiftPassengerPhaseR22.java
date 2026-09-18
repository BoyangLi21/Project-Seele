package com.projectseele.world;
import net.minecraft.world.entity.player.Player;
import java.util.function.BiConsumer;
/** Optional client hook, avoiding a dedicated-server dependency on client classes. */
public final class LiftPassengerPhaseR22
{
    public static BiConsumer<Player,Double> afterClientCarry=(p,dy)->{};
    private LiftPassengerPhaseR22(){}
}
