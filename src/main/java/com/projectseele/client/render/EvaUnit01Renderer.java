package com.projectseele.client.render;

import java.util.Set;
import java.util.function.Consumer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.client.ClientForgeEvents;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.culling.Frustum;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.resources.ResourceLocation;
import org.jetbrains.annotations.Nullable;
import software.bernie.geckolib.cache.object.BakedGeoModel;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.renderer.GeoEntityRenderer;

/**
 * GeckoLib-driven EVA renderer.
 *
 * GeckoLib is the sole authority for body and arm poses. First person observes
 * this same world-space skeleton from the pilot's head socket. Only mesh
 * shells that physically enclose the camera are suppressed. The sole special
 * case is the building-sized positron cannon: its first-person geometry is
 * stowed in favour of the entry-plug optical feed; third person remains the
 * authoritative world skeleton. There is no detached arm viewmodel.
 */
public class EvaUnit01Renderer extends GeoEntityRenderer<EvaUnit01Entity>
{
    private static final ResourceLocation MESH_00 =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_unit00.mesh.json");
    private static final ResourceLocation MESH_01 =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_unit01.mesh.json");
    private static final ResourceLocation MESH_02 =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_unit02.mesh.json");
    private static final ResourceLocation TEXTURE_00 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit00.png");
    private static final ResourceLocation TEXTURE_01 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit01.png");
    private static final ResourceLocation TEXTURE_02 =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_unit02.png");
    private static final ResourceLocation POSITRON_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/positron_cannon.mesh.json");
    private static final ResourceLocation POSITRON_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/positron_cannon.png");
    private static final ResourceLocation RIFLE_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_pallet_smg.mesh.json");
    private static final ResourceLocation RIFLE_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_pallet_smg.png");
    private static final ResourceLocation N2_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva_n2_device.mesh.json");
    private static final ResourceLocation N2_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva_n2_device.png");
    private static final ResourceLocation COMMON_KNIFE_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/progressive_knife.mesh.json");
    private static final ResourceLocation COMMON_KNIFE_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/progressive_knife.png");
    private static final ResourceLocation UNIT02_KNIFE_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva02_knife.mesh.json");
    private static final ResourceLocation UNIT02_SPECIAL_WEAPON_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/eva02_special_weapon.mesh.json");
    private static final ResourceLocation UNIT02_WEAPONS_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/eva02_weapons.png");
    private static final ResourceLocation ENTRY_PLUG_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/entry_plug.mesh.json");
    private static final ResourceLocation ENTRY_PLUG_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/entry_plug.png");
    private static final ResourceLocation LONGINUS_MESH =
            new ResourceLocation(ProjectSeele.MODID, "mesh/longinus_lance.mesh.json");
    private static final ResourceLocation LONGINUS_TEXTURE =
            new ResourceLocation(ProjectSeele.MODID, "textures/entity/longinus_lance.png");
    private static final Set<String> CAMERA_COVER_BONES = Set.of(
            "head", "Head", "horn", "Horn", "neck", "Neck");
    private static final Set<String> PILOT_CAMERA_MESH_COVER = Set.of(
            "torso_lower", "torso_upper", "pylon_l", "pylon_r");
    private boolean pilotView;
    private boolean strictFailureReported;

    public EvaUnit01Renderer(EntityRendererProvider.Context context)
    {
        super(context, new EvaUnit01GeoModel());
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> meshResourceForVariant(entity.getUnitVariant()),
                entity -> textureResourceForVariant(entity.getUnitVariant()),
                this::shouldRenderBodyMesh));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                EvaUnit01Renderer::knifeMeshResource,
                EvaUnit01Renderer::knifeTextureResource,
                (entity, bone) -> entity.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE
                        && "knife".equals(bone.getName())));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> POSITRON_MESH, entity -> POSITRON_TEXTURE,
                (entity, bone) -> entity.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                        && "cannon".equals(bone.getName())));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> RIFLE_MESH, entity -> RIFLE_TEXTURE,
                (entity, bone) -> entity.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                        && "cannon".equals(bone.getName())));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> N2_MESH, entity -> N2_TEXTURE,
                (entity, bone) -> entity.getWeapon() == EvaUnit01Entity.WEAPON_N2
                        && "n2".equals(bone.getName())));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                EvaUnit01Renderer::lanceMeshResource,
                EvaUnit01Renderer::lanceTextureResource,
                (entity, bone) -> entity.getWeapon() == EvaUnit01Entity.WEAPON_LANCE
                        && "lance".equals(bone.getName())));
        this.addRenderLayer(new LocalTriangleMeshLayer<>(this,
                entity -> ENTRY_PLUG_MESH, entity -> ENTRY_PLUG_TEXTURE,
                (entity, bone) -> !this.pilotView
                        && isEntryHardwareVisible(entity, bone.getName())));
        this.shadowRadius = 3.6F;
        this.withScale(2.5F);
    }

    @Override
    public void render(EvaUnit01Entity entity, float entityYaw, float partialTick, PoseStack poseStack,
                       MultiBufferSource bufferSource, int packedLight)
    {
        LocalVisualAssetFingerprint.Fingerprint fingerprint =
                visualFingerprintForVariant(entity.getUnitVariant());
        if (LocalVisualAssetFingerprint.isStrictMode() && !fingerprint.valid())
        {
            if (!this.strictFailureReported)
            {
                this.strictFailureReported = true;
                ProjectSeele.LOGGER.error(
                        "Strict high-detail EVA render refused: {}", fingerprint.description());
            }
            return;
        }
        Minecraft minecraft = Minecraft.getInstance();
        this.pilotView = minecraft.options.getCameraType().isFirstPerson()
                && minecraft.getCameraEntity() != null
                && minecraft.getCameraEntity().getVehicle() == entity;
        super.render(entity, entityYaw, partialTick, poseStack, bufferSource,
                entity.isCrucified() ? LightTexture.FULL_BRIGHT : packedLight);
    }

    @Override
    public boolean shouldRender(EvaUnit01Entity entity, Frustum frustum,
                                double cameraX, double cameraY, double cameraZ)
    {
        Minecraft minecraft = Minecraft.getInstance();
        // The crouch/prone head socket can sit just beyond the entity's coarse
        // gameplay AABB while hands and weapon remain in front of the camera.
        // Do not let frustum culling make the shared body disappear only in
        // first person; every other observer keeps the normal culling path.
        if (minecraft.options.getCameraType().isFirstPerson()
                && minecraft.getCameraEntity() != null
                && minecraft.getCameraEntity().getVehicle() == entity)
        {
            return true;
        }
        return super.shouldRender(entity, frustum, cameraX, cameraY, cameraZ);
    }

    @Override
    public void preRender(PoseStack poseStack, EvaUnit01Entity animatable, BakedGeoModel model,
                          @Nullable MultiBufferSource bufferSource, @Nullable VertexConsumer buffer,
                          boolean isReRender, float partialTick, int packedLight, int packedOverlay,
                          float red, float green, float blue, float alpha)
    {
        super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender,
                partialTick, packedLight, packedOverlay, red, green, blue, alpha);
        forEachBone(model, bone ->
        {
            bone.setHidden(false);
            bone.setChildrenHidden(false);
        });
        if (this.pilotView)
        {
            forEachBone(model, bone ->
            {
                if (CAMERA_COVER_BONES.contains(bone.getName()))
                {
                    hideSubtree(bone);
                }
            });
            // The long weapons only leave the physical camera feed while an
            // optical sight is actually active. Keeping the aim subtree for
            // the clean first-person pass lets visual regression captures
            // inspect the same arms and weapon that third person renders;
            // holding RMB switches to the entry-plug fire-control picture.
            if (ClientForgeEvents.isCannonScopeActive(animatable)
                    || ClientForgeEvents.isRifleSightActive(animatable))
            {
                model.getBone("aim_pitch").ifPresent(EvaUnit01Renderer::hideSubtree);
            }
        }
        // This is a small additive elevation layer on the one world skeleton,
        // after GeckoLib has evaluated the authored two-hand cannon stance.
        // The imported rig gives both arms a shared shoulder-space parent so
        // pitch never rotates the head/chest away from the fixed pilot socket.
        // First and third person therefore observe the same hands, receiver
        // and physical pitch limit without the cockpit camera falling inside
        // the torso whenever the pilot looks up or down.
        if (!isReRender)
        {
            if (model.getBone("aim_pitch").isPresent())
            {
                // aim_pitch is an unanimated semantic parent owned solely by
                // this renderer. Assign the requested pitch absolutely on
                // every primary pass. Adding to its previous value made each
                // frame (and each render layer) accumulate another camera
                // angle, producing the view-dependent "windmill" rotation.
                float pitch = animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                        || animatable.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                        ? (float) Math.toRadians(animatable.getCannonAimPitch()) : 0.0F;
                // Minecraft's positive XRot looks down; the imported Bedrock
                // aim parent uses the opposite positive-X convention. The hit
                // ray keeps the Minecraft sign, while the visible rig must use
                // its negation or mouse-up visibly points the barrel down.
                model.getBone("aim_pitch").get().setRotX(-pitch);
            }
            else if (animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON)
            {
                // Public fallback rigs pre-date the semantic aim parent. Do
                // not mutate their animated arm bones here: an additive
                // fallback cannot be idempotent across Gecko render layers.
                // Their authored aim pose remains stable until regenerated
                // with the current semantic-parent converter.
            }
        }
        // Weapon visibility applies on top in every view.
        setWeaponVisibility(model, "knife", animatable.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE);
        setWeaponVisibility(model, "cannon", animatable.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                || animatable.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE);
        setWeaponVisibility(model, "lance", animatable.getWeapon() == EvaUnit01Entity.WEAPON_LANCE);
        setWeaponVisibility(model, "n2", animatable.getWeapon() == EvaUnit01Entity.WEAPON_N2);
        boolean shieldBrace = animatable.isShieldBraced()
                || (animatable.getUnitVariant() == EvaUnit01Entity.UNIT_00
                    && animatable.getVisualPose() == EvaUnit01Entity.VISUAL_CROUCH);
        setWeaponVisibility(model, "shield", shieldBrace);
        // Only the travelling portion of the plug is outside the armour.  At
        // the end of insertion it is physically below the dorsal socket; the
        // closed hatch remains visible, but rendering the full 38px capsule at
        // its zero transform made it stick out of the EVA forever.
        boolean plugTravelling = !this.pilotView && isEntryPlugTravelling(animatable);
        setWeaponVisibility(model, "entry_plug", plugTravelling);
        setWeaponVisibility(model, "plug_hatch_l", !this.pilotView);
        setWeaponVisibility(model, "plug_hatch_r", !this.pilotView);
    }

    private static void setWeaponVisibility(BakedGeoModel model, String name, boolean active)
    {
        model.getBone(name).ifPresent(bone ->
                bone.setHidden(bone.isHidden() || !active));
    }

    @Override
    public void renderCubesOfBone(PoseStack poseStack, GeoBone bone, VertexConsumer buffer,
                                  int packedLight, int packedOverlay, float red, float green,
                                  float blue, float alpha)
    {
        EvaUnit01Entity entity = this.getAnimatable();
        boolean bodyMesh = entity != null && LocalTriangleMeshLayer.hasPart(
                meshResourceForVariant(entity.getUnitVariant()), bone.getName());
        boolean cannonMesh = entity != null
                && entity.getWeapon() == EvaUnit01Entity.WEAPON_CANNON
                && "cannon".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(POSITRON_MESH, bone.getName());
        boolean rifleMesh = entity != null
                && entity.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                && "cannon".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(RIFLE_MESH, bone.getName());
        boolean n2Mesh = entity != null
                && entity.getWeapon() == EvaUnit01Entity.WEAPON_N2
                && "n2".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(N2_MESH, bone.getName());
        ResourceLocation activeKnifeMesh = entity == null ? COMMON_KNIFE_MESH
                : knifeMeshResource(entity);
        boolean knifeMesh = entity != null
                && entity.getWeapon() == EvaUnit01Entity.WEAPON_KNIFE
                && "knife".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(activeKnifeMesh, bone.getName());
        boolean entryHardwareMesh = !this.pilotView && entity != null
                && isEntryHardwareVisible(entity, bone.getName())
                && LocalTriangleMeshLayer.hasPart(ENTRY_PLUG_MESH, bone.getName());
        ResourceLocation activeLanceMesh = entity == null ? LONGINUS_MESH
                : lanceMeshResource(entity);
        boolean lanceMesh = entity != null
                && entity.getWeapon() == EvaUnit01Entity.WEAPON_LANCE
                && "lance".equals(bone.getName())
                && LocalTriangleMeshLayer.hasPart(activeLanceMesh, bone.getName());
        if (bodyMesh || cannonMesh || rifleMesh || n2Mesh
                || knifeMesh || lanceMesh || entryHardwareMesh)
        {
            return;
        }
        super.renderCubesOfBone(poseStack, bone, buffer, packedLight, packedOverlay,
                red, green, blue, alpha);
    }

    /**
     * The 6s activation clip seats the capsule at 3.15s, then spends the
     * remaining time closing the hatch and bringing the EVA online.  Keeping
     * the plug rendered for all 120 ticks exposes it through seams after it is
     * already internal, so stop drawing it at that authored seating frame.
     */
    private static boolean isEntryPlugTravelling(EvaUnit01Entity entity)
    {
        return entity.getActivationTicks() > 57;
    }

    private static boolean isEntryHardwareVisible(EvaUnit01Entity entity, String boneName)
    {
        return "plug_hatch_l".equals(boneName) || "plug_hatch_r".equals(boneName)
                || ("entry_plug".equals(boneName) && isEntryPlugTravelling(entity));
    }

    public static ResourceLocation meshResourceForVariant(int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> MESH_00;
            case EvaUnit01Entity.UNIT_02 -> MESH_02;
            default -> MESH_01;
        };
    }

    /** Keep body vertices on a variant-owned buffer, never a weapon buffer. */
    public static ResourceLocation textureResourceForVariant(int variant)
    {
        return switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> TEXTURE_00;
            case EvaUnit01Entity.UNIT_02 -> TEXTURE_02;
            default -> TEXTURE_01;
        };
    }

    public static ResourceLocation positronMeshResource()
    {
        return POSITRON_MESH;
    }

    public static ResourceLocation rifleMeshResource()
    {
        return RIFLE_MESH;
    }

    public static ResourceLocation n2MeshResource()
    {
        return N2_MESH;
    }

    public static ResourceLocation knifeMeshResource(EvaUnit01Entity entity)
    {
        return entity.getUnitVariant() == EvaUnit01Entity.UNIT_02
                ? UNIT02_KNIFE_MESH : COMMON_KNIFE_MESH;
    }

    private static ResourceLocation knifeTextureResource(EvaUnit01Entity entity)
    {
        return entity.getUnitVariant() == EvaUnit01Entity.UNIT_02
                ? UNIT02_WEAPONS_TEXTURE : COMMON_KNIFE_TEXTURE;
    }

    public static ResourceLocation lanceMeshResource(EvaUnit01Entity entity)
    {
        // Until Unit-02's dedicated weapon has its own reviewed stance, all
        // three pilotable EVAs use the same Longinus geometry and two-hand
        // spear contract.  The old rebuild sword occupied this socket like a
        // chest-mounted blade instead of a polearm.
        return LONGINUS_MESH;
    }

    private static ResourceLocation lanceTextureResource(EvaUnit01Entity entity)
    {
        return LONGINUS_TEXTURE;
    }

    public static LocalVisualAssetFingerprint.Fingerprint visualFingerprintForVariant(int variant)
    {
        return LocalVisualAssetFingerprint.inspect(switch (variant)
        {
            case EvaUnit01Entity.UNIT_00 -> "eva_unit00";
            case EvaUnit01Entity.UNIT_02 -> "eva_unit02";
            default -> "eva_unit01";
        });
    }

    private boolean shouldRenderBodyMesh(EvaUnit01Entity entity, GeoBone bone)
    {
        if (!this.pilotView)
        {
            return true;
        }
        if (CAMERA_COVER_BONES.contains(bone.getName()))
        {
            return false;
        }
        // The rider socket is fixed to the entity while attack animations can
        // rotate the chest through that socket.  Suppress only the four rigid
        // shells enclosing the pilot in every stance; never hide their bones
        // or descendants.  Arms, hands, fingers and weapons therefore remain
        // the exact world skeleton seen by third person without the chest
        // becoming an opaque wall during a knife strike or spear lunge.
        return !PILOT_CAMERA_MESH_COVER.contains(bone.getName());
    }

    private static void hideSubtree(GeoBone bone)
    {
        bone.setHidden(true);
        bone.setChildrenHidden(true);
        for (GeoBone child : bone.getChildBones())
        {
            hideSubtree(child);
        }
    }

    private static void forEachBone(BakedGeoModel model, Consumer<GeoBone> action)
    {
        for (GeoBone bone : model.topLevelBones())
        {
            walkBone(bone, action);
        }
    }

    private static void walkBone(GeoBone bone, Consumer<GeoBone> action)
    {
        action.accept(bone);
        for (GeoBone child : bone.getChildBones())
        {
            walkBone(child, action);
        }
    }
}
