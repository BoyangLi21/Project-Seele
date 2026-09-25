package com.projectseele.mixin.client;

import com.projectseele.client.CommandShaderLightR39;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Pseudo
@Mixin(targets="net.irisshaders.iris.uniforms.CommonUniforms",remap=false)
public abstract class CommandShaderLightR39Mixin
{
    @Inject(method="addNonDynamicUniforms",at=@At("TAIL"),remap=false)
    private static void seele$commandLight(@Coerce Object uniforms,@Coerce Object idMap,
            @Coerce Object directives,@Coerce Object notifier,CallbackInfo ci)
    {CommandShaderLightR39.bind(uniforms);}
}
