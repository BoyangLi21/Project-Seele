package com.projectseele.combat;

import com.projectseele.registry.ModItems;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;

/** Shared checks for damage sources that ignore an A.T. Field entirely. */
public final class AtFieldRules
{
    private AtFieldRules() {}

    public static boolean bypassesAtField(DamageSource source)
    {
        if (!(source.getEntity() instanceof LivingEntity attacker))
        {
            return false;
        }
        return attacker.getMainHandItem().is(ModItems.LANCE_OF_LONGINUS.get())
                || attacker instanceof EvaUnit01Entity eva
                && eva.getWeapon() == EvaUnit01Entity.WEAPON_LANCE;
    }
}
