package com.projectseele.world;

import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.block.Block;

/** Old saves remain recognisable while new construction uses painted structural panels. */
public final class NervMaterials
{
    public static final TagKey<Block> STRUCTURAL_SHELL = TagKey.create(
            Registries.BLOCK, new ResourceLocation("projectseele", "structural_shell"));

    public static Block structuralBlock(){return com.projectseele.registry.ModBlocks.NERV_STRUCTURAL_PANEL.get();}

    private NervMaterials() {}
}
