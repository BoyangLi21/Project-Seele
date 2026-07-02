package com.projectseele;

import com.mojang.logging.LogUtils;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import org.slf4j.Logger;

// The value here should match an entry in the META-INF/mods.toml file
@Mod(ProjectSeele.MODID)
public class ProjectSeele
{
    // Define mod id in a common place for everything to reference
    public static final String MODID = "projectseele";
    public static final Logger LOGGER = LogUtils.getLogger();

    public ProjectSeele(FMLJavaModLoadingContext context)
    {
        context.getModEventBus().addListener(this::commonSetup);
    }

    private void commonSetup(final FMLCommonSetupEvent event)
    {
        LOGGER.info("Project SEELE initialized. God's in his heaven, all's right with the world.");
    }
}
