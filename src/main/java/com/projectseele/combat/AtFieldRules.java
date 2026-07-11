package com.projectseele.combat;

import com.projectseele.registry.ModItems;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;

/** Shared checks for damage sources that ignore an A.T. Field entirely. */
public final class AtFieldRules
{
    private AtFieldRules() {}

    public static boolean bypassesAtField(DamageSource source)
    {
        return source.getEntity() instanceof LivingEntity attacker
                && attacker.getMainHandItem().is(ModItems.LANCE_OF_LONGINUS.get());
    }
}
