package com.projectseele.mixin;

import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.entity.EntitySectionStorage;
import net.minecraft.world.level.entity.PersistentEntitySectionManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(PersistentEntitySectionManager.class)
public interface ServiceAircraftSectionsR32Accessor
{
    @Accessor("sectionStorage")
    EntitySectionStorage<Entity> seele$sectionsR32();
}
