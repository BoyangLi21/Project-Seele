package com.projectseele.network;

import com.projectseele.ProjectSeele;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

/**
 * The mod's single wire protocol. All cross-side interaction goes through
 * here — clients never guess server state.
 */
public final class SeeleNetwork
{
    private static final String PROTOCOL_VERSION = "4";

    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(ProjectSeele.MODID, "main"),
            () -> PROTOCOL_VERSION, PROTOCOL_VERSION::equals, PROTOCOL_VERSION::equals);

    private SeeleNetwork() {}

    public static void register()
    {
        int id = 0;
        CHANNEL.messageBuilder(ClientboundCrossExplosionPacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundCrossExplosionPacket::encode)
                .decoder(ClientboundCrossExplosionPacket::new)
                .consumerMainThread(ClientboundCrossExplosionPacket::handle)
                .add();
        CHANNEL.messageBuilder(ClientboundAlarmPacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundAlarmPacket::encode)
                .decoder(ClientboundAlarmPacket::new)
                .consumerMainThread(ClientboundAlarmPacket::handle)
                .add();
        CHANNEL.messageBuilder(ClientboundAtFieldRipplePacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundAtFieldRipplePacket::encode)
                .decoder(ClientboundAtFieldRipplePacket::new)
                .consumerMainThread(ClientboundAtFieldRipplePacket::handle)
                .add();
        CHANNEL.messageBuilder(ClientboundCannonBeamPacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundCannonBeamPacket::encode)
                .decoder(ClientboundCannonBeamPacket::new)
                .consumerMainThread(ClientboundCannonBeamPacket::handle)
                .add();
        CHANNEL.messageBuilder(ClientboundNukeFxPacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundNukeFxPacket::encode)
                .decoder(ClientboundNukeFxPacket::new)
                .consumerMainThread(ClientboundNukeFxPacket::handle)
                .add();
        CHANNEL.messageBuilder(ClientboundThirdImpactPacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundThirdImpactPacket::encode)
                .decoder(ClientboundThirdImpactPacket::new)
                .consumerMainThread(ClientboundThirdImpactPacket::handle)
                .add();
        CHANNEL.messageBuilder(ClientboundVisualCapturePacket.class, id++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(ClientboundVisualCapturePacket::encode)
                .decoder(ClientboundVisualCapturePacket::new)
                .consumerMainThread(ClientboundVisualCapturePacket::handle)
                .add();
        CHANNEL.messageBuilder(ServerboundEvaControlPacket.class, id++, NetworkDirection.PLAY_TO_SERVER)
                .encoder(ServerboundEvaControlPacket::encode)
                .decoder(ServerboundEvaControlPacket::new)
                .consumerMainThread(ServerboundEvaControlPacket::handle)
                .add();
        CHANNEL.messageBuilder(ServerboundEntryPlugPacket.class, id++, NetworkDirection.PLAY_TO_SERVER)
                .encoder(ServerboundEntryPlugPacket::encode)
                .decoder(ServerboundEntryPlugPacket::new)
                .consumerMainThread(ServerboundEntryPlugPacket::handle)
                .add();
    }
}
