package com.projectseele.client.render;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.ArrayList;
import java.util.Optional;
import java.util.Set;
import java.util.function.Function;
import java.util.function.BiPredicate;
import java.util.zip.CRC32;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import com.projectseele.ProjectSeele;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.LightTexture;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.Resource;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.world.phys.Vec3;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.core.animatable.GeoAnimatable;
import software.bernie.geckolib.renderer.GeoRenderer;
import software.bernie.geckolib.renderer.layer.GeoRenderLayer;

/**
 * Optional local-only triangle geometry driven by a GeckoLib bone hierarchy.
 * The public jar contains the loader but no third-party mesh or texture.
 */
public final class LocalTriangleMeshLayer<T extends GeoAnimatable> extends GeoRenderLayer<T>
{
    private static final Map<ResourceLocation, MeshData> CACHE = new HashMap<>();
    private static final Set<ResourceLocation> LOAD_ATTEMPTED = new HashSet<>();
    private final Function<T, ResourceLocation> meshSelector;
    private final Function<T, ResourceLocation> textureSelector;
    private final BiPredicate<T, GeoBone> partVisibility;
    private final boolean fullBright;

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector)
    {
        this(renderer, meshSelector, null, (entity, bone) -> true, false);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector)
    {
        this(renderer, meshSelector, textureSelector,
                (entity, bone) -> true, false);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector,
                                  BiPredicate<T, GeoBone> partVisibility)
    {
        this(renderer, meshSelector, textureSelector, partVisibility, false);
    }

    public LocalTriangleMeshLayer(GeoRenderer<T> renderer,
                                  Function<T, ResourceLocation> meshSelector,
                                  Function<T, ResourceLocation> textureSelector,
                                  BiPredicate<T, GeoBone> partVisibility,
                                  boolean fullBright)
    {
        super(renderer);
        this.meshSelector = meshSelector;
        this.textureSelector = textureSelector;
        this.partVisibility = partVisibility;
        this.fullBright = fullBright;
    }

    @Override
    public void renderForBone(PoseStack poseStack, T animatable, GeoBone bone,
                              RenderType renderType, MultiBufferSource bufferSource,
                              VertexConsumer buffer, float partialTick, int packedLight,
                              int packedOverlay)
    {
        if (bone.isHidden() || !this.partVisibility.test(animatable, bone))
        {
            return;
        }
        ResourceLocation meshLocation = this.meshSelector.apply(animatable);
        MeshData mesh = getMesh(meshLocation);
        if (mesh == null)
        {
            return;
        }
        MeshPart part = mesh.parts().get(bone.getName());
        if (part == null)
        {
            return;
        }

        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        if(com.projectseele.client.visual.EvaDorsalR13Audit.ENABLED&&!this.fullBright&&animatable instanceof EvaUnit01Entity eva
                &&this.getRenderer() instanceof EvaUnit01Renderer renderer)
            com.projectseele.client.visual.EvaDorsalR13Audit.capture(eva,bone.getName(),renderer.renderedMeshTransform(pose,eva,partialTick));
        if (animatable instanceof EvaUnit01Entity eva
                && eva.getWeapon() == EvaUnit01Entity.WEAPON_RIFLE
                && "cannon".equals(bone.getName())
                && meshLocation.getPath().endsWith("eva_pallet_smg.mesh.json"))
        {
            if (this.getRenderer() instanceof EvaUnit01Renderer renderer)
                EvaUnit01Renderer.rememberRifleMuzzle(eva.getId(), renderer.renderedMeshPoint(
                        pose, new Vector3f(part.muzzleX(), part.muzzleY(), part.muzzleZ()), eva, partialTick));
        }
        VertexConsumer targetBuffer = this.textureSelector == null ? buffer
                : bufferSource.getBuffer(RenderType.entityCutoutNoCull(
                        this.textureSelector.apply(animatable)));
        float[] values = skinVertices(mesh,part,bone);
        int stride = mesh.stride();
        if(Boolean.getBoolean("projectseele.motionReviewR05")&&!this.fullBright&&animatable instanceof EvaUnit01Entity eva
                &&this.getRenderer() instanceof EvaUnit01Renderer renderer)
            com.projectseele.client.visual.EvaMeshAuditR05.capture(eva.getId(),meshLocation.getPath().contains("pallet_smg")?"rifle":bone.getName(),
                    values,stride,part.pivotX(),part.pivotY(),part.pivotZ(),renderer.renderedMeshTransform(pose,eva,partialTick));
        int vertexLight = this.fullBright
                ? LightTexture.FULL_BRIGHT : packedLight;
        for (int index = 0; index + stride * 3 <= values.length; index += stride * 3)
        {
            emitVertex(targetBuffer, pose, normal, values, index, part,
                    vertexLight, packedOverlay);
            emitVertex(targetBuffer, pose, normal, values, index + stride, part,
                    vertexLight, packedOverlay);
            emitVertex(targetBuffer, pose, normal, values, index + stride * 2, part,
                    vertexLight, packedOverlay);
            // Gecko's entity cutout buffer is QUADS. A repeated third point
            // makes each OBJ triangle an independent degenerate quad.
            emitVertex(targetBuffer, pose, normal, values, index + stride * 2, part,
                    vertexLight, packedOverlay);
        }
    }

    private static void emitVertex(VertexConsumer buffer, Matrix4f pose, Matrix3f normal,
                                   float[] values, int index, MeshPart part,
                                   int packedLight, int packedOverlay)
    {
        // Match GeckoLib's Bedrock X reflection so cubes and local triangles
        // occupy the same animated coordinate space.
        float x = -(values[index] + part.pivotX()) / 16.0F;
        float y = (values[index + 1] + part.pivotY()) / 16.0F;
        float z = (values[index + 2] + part.pivotZ()) / 16.0F;
        MeshVertexWriter.emit(buffer,pose,normal,x,y,z,values[index+3],values[index+4],
                packedLight,packedOverlay,-values[index+5],values[index+6],values[index+7]);
    }

    public static void clearCache()
    {
        CACHE.clear();
        LOAD_ATTEMPTED.clear();
        EvaHeadClearance.clear();
    }

    static float[] nativeTrianglePositions(ResourceLocation resource,String name)
    {
        MeshData mesh=getMesh(resource);if(mesh==null)return null;
        MeshPart part=mesh.parts().get(name);if(part==null)return null;
        float[] source=part.vertices(),result=new float[source.length/mesh.stride()*3];
        for(int i=0,j=0;i<source.length;i+=mesh.stride(),j+=3)
        {
            result[j]=-(source[i]+part.pivotX())/16;
            result[j+1]=(source[i+1]+part.pivotY())/16;
            result[j+2]=(source[i+2]+part.pivotZ())/16;
        }
        return result;
    }

    /**
     * Parses the large local EVA shells while the resource reload screen still
     * owns the render thread. Lazy parsing after an EVA first enters view can
     * otherwise create multi-second frame stalls in an ordinary route walk.
     */
    public static void prewarm(ResourceManager resourceManager,
                               ResourceLocation... meshResources)
    {
        long startedAt = System.nanoTime();
        int loaded = 0;
        for (ResourceLocation meshResource : meshResources)
        {
            if (getMesh(resourceManager, meshResource) != null)
            {
                loaded++;
            }
        }
        ProjectSeele.LOGGER.info(
                "Prewarmed local triangle meshes: loaded={}/{} elapsedMs={}",
                loaded, meshResources.length,
                (System.nanoTime() - startedAt) / 1_000_000L);
    }

    public static boolean hasPart(ResourceLocation meshResource, String boneName)
    {
        MeshData mesh = getMesh(meshResource);
        return mesh != null && mesh.parts().containsKey(boneName);
    }

    /**
     * Renders a local attachment mesh as one independent world object.
     * Weapon elevators use this path so the payload stays a real persistent
     * entity before it is handed to the EVA skeleton.  The mesh is centred on
     * X/Z and rests on local Y=0; caller scale/orientation remains explicit.
     */
    public static boolean renderStandalone(PoseStack poseStack,
                                           MultiBufferSource bufferSource,
                                           ResourceLocation meshResource,
                                           ResourceLocation textureResource,
                                           int packedLight,
                                           int packedOverlay)
    {
        MeshData mesh = getMesh(meshResource);
        if (mesh == null)
        {
            return false;
        }
        VertexConsumer target = bufferSource.getBuffer(
                RenderType.entityCutoutNoCull(textureResource));
        Matrix4f pose = poseStack.last().pose();
        Matrix3f normal = poseStack.last().normal();
        for (MeshPart part : mesh.parts().values())
        {
            float[] values = part.vertices();
            for (int index = 0; index + mesh.stride() * 3 <= values.length;
                 index += mesh.stride() * 3)
            {
                emitStandaloneVertex(target, pose, normal, values, index,
                        part, mesh, packedLight, packedOverlay);
                emitStandaloneVertex(target, pose, normal, values,
                        index + mesh.stride(), part, mesh,
                        packedLight, packedOverlay);
                emitStandaloneVertex(target, pose, normal, values,
                        index + mesh.stride() * 2, part, mesh,
                        packedLight, packedOverlay);
                emitStandaloneVertex(target, pose, normal, values,
                        index + mesh.stride() * 2, part, mesh,
                        packedLight, packedOverlay);
            }
        }
        return true;
    }

    private static void emitStandaloneVertex(VertexConsumer buffer,
                                             Matrix4f pose, Matrix3f normal,
                                             float[] values, int index,
                                             MeshPart part, MeshData mesh,
                                             int packedLight,
                                             int packedOverlay)
    {
        float absoluteX = values[index] + part.pivotX();
        float absoluteY = values[index + 1] + part.pivotY();
        float absoluteZ = values[index + 2] + part.pivotZ();
        float x = -(absoluteX - mesh.centreX()) / 16.0F;
        float y = (absoluteY - mesh.minimumY()) / 16.0F;
        float z = (absoluteZ - mesh.centreZ()) / 16.0F;
        MeshVertexWriter.emit(buffer,pose,normal,x,y,z,values[index+3],values[index+4],
                packedLight,packedOverlay,-values[index+5],values[index+6],values[index+7]);
    }

    public static String captureTag(ResourceLocation meshResource)
    {
        MeshData mesh = getMesh(meshResource);
        return mesh == null ? "mesh-missing" : mesh.captureTag();
    }

    private static MeshData getMesh(ResourceLocation meshLocation)
    {
        return getMesh(Minecraft.getInstance().getResourceManager(),
                meshLocation);
    }

    private static MeshData getMesh(ResourceManager resourceManager,
                                    ResourceLocation meshLocation)
    {
        if (LOAD_ATTEMPTED.contains(meshLocation))
        {
            return CACHE.get(meshLocation);
        }
        LOAD_ATTEMPTED.add(meshLocation);
        Optional<Resource> resource = resourceManager.getResource(meshLocation);
        if (resource.isEmpty())
        {
            return null;
        }
        try (var stream = resource.get().open())
        {
            byte[] bytes = stream.readAllBytes();
            JsonObject root = JsonParser.parseString(
                    new String(bytes, StandardCharsets.UTF_8)).getAsJsonObject();
            int stride = root.get("stride").getAsInt();
            if (stride != 8)
            {
                throw new IOException("Unsupported local mesh stride " + stride);
            }
            Map<String, MeshPart> parts = new HashMap<>();
            for (Map.Entry<String, JsonElement> entry : root.getAsJsonObject("parts").entrySet())
            {
                JsonObject object = entry.getValue().getAsJsonObject();
                JsonArray pivot = object.getAsJsonArray("pivot");
                JsonArray source = object.getAsJsonArray("vertices");
                if (pivot.size() != 3 || source.size() == 0)
                {
                    throw new IOException("Invalid local mesh part " + entry.getKey());
                }
                float[] vertices = new float[source.size()];
                for (int index = 0; index < source.size(); index++)
                {
                    vertices[index] = source.get(index).getAsFloat();
                    if (!Float.isFinite(vertices[index]))
                    {
                        throw new IOException("Non-finite vertex in " + entry.getKey());
                    }
                }
                if (vertices.length % (stride * 3) != 0)
                {
                    throw new IOException("Incomplete triangles in " + entry.getKey());
                }
                float pivotX = pivot.get(0).getAsFloat();
                float pivotY = pivot.get(1).getAsFloat();
                float pivotZ = pivot.get(2).getAsFloat();
                float[] muzzle = farCap(vertices, stride,
                        pivotX, pivotY, pivotZ);
                parts.put(entry.getKey(), new MeshPart(
                        pivotX, pivotY, pivotZ, vertices,
                        muzzle[0], muzzle[1], muzzle[2]));
            }
            int triangleCount = parts.values().stream()
                    .mapToInt(part -> part.vertices().length / (stride * 3)).sum();
            CRC32 crc = new CRC32();
            crc.update(bytes);
            String captureTag = String.format("triangle-mesh-%d-p%d-%08x",
                    triangleCount, parts.size(), crc.getValue());
            float minimumX = Float.POSITIVE_INFINITY;
            float minimumY = Float.POSITIVE_INFINITY;
            float minimumZ = Float.POSITIVE_INFINITY;
            float maximumX = Float.NEGATIVE_INFINITY;
            float maximumZ = Float.NEGATIVE_INFINITY;
            for (MeshPart part : parts.values())
            {
                float[] values = part.vertices();
                for (int index = 0; index < values.length; index += stride)
                {
                    float x = values[index] + part.pivotX();
                    float y = values[index + 1] + part.pivotY();
                    float z = values[index + 2] + part.pivotZ();
                    minimumX = Math.min(minimumX, x);
                    minimumY = Math.min(minimumY, y);
                    minimumZ = Math.min(minimumZ, z);
                    maximumX = Math.max(maximumX, x);
                    maximumZ = Math.max(maximumZ, z);
                }
            }
            MeshData mesh = new MeshData(stride, Map.copyOf(parts),
                    triangleCount, captureTag,
                    (minimumX + maximumX) * 0.5F, minimumY,
                    (minimumZ + maximumZ) * 0.5F, jointSkins(parts,stride));
            CACHE.put(meshLocation, mesh);
            ProjectSeele.LOGGER.info("Loaded local triangle mesh {}: {}",
                    meshLocation, captureTag);
            return mesh;
        }
        catch (Exception exception)
        {
            ProjectSeele.LOGGER.error("Failed to load local triangle mesh " + meshLocation,
                    exception);
            return null;
        }
    }

    private static float[] farCap(float[] vertices, int stride,
                                  float pivotX, float pivotY, float pivotZ)
    {
        float minimumY = Float.POSITIVE_INFINITY;
        for (int index = 0; index < vertices.length; index += stride)
        {
            minimumY = Math.min(minimumY, vertices[index + 1]);
        }
        float sumX = 0.0F;
        float sumY = 0.0F;
        float sumZ = 0.0F;
        int samples = 0;
        for (int index = 0; index < vertices.length; index += stride)
        {
            if (vertices[index + 1] > minimumY + 0.85F)
            {
                continue;
            }
            sumX += vertices[index] + pivotX;
            sumY += vertices[index + 1] + pivotY;
            sumZ += vertices[index + 2] + pivotZ;
            samples++;
        }
        if (samples == 0)
        {
            return new float[] {-pivotX / 16.0F,
                    pivotY / 16.0F, pivotZ / 16.0F};
        }
        return new float[] {-(sumX / samples) / 16.0F,
                (sumY / samples) / 16.0F,
                (sumZ / samples) / 16.0F};
    }

    private record MeshData(int stride, Map<String, MeshPart> parts,
                            int triangleCount, String captureTag,
                            float centreX, float minimumY,
                            float centreZ,Map<String,JointSkin> joints) {}

    private record JointSkin(String other,float[] weights,float[] rest,float[] scratch) {}

    private static Vector3f restPoint(MeshPart p,int offset)
    {
        return new Vector3f(p.vertices()[offset]+p.pivotX(),
                p.vertices()[offset+1]+p.pivotY(),p.vertices()[offset+2]+p.pivotZ());
    }

    private static Map<String,JointSkin> jointSkins(Map<String,MeshPart> parts,int stride)
    {
        Map<String,JointSkin> result=new HashMap<>();
        for(String joint:new String[]{"elbow","ankle"})for(String side:new String[]{"l","r"})
        {
            String upper=(joint.equals("elbow")?"arm_":"shin_")+side,lower=(joint.equals("elbow")?"forearm_":"foot_")+side;
            var a=parts.get(upper);var b=parts.get(lower);if(a==null||b==null)continue;
            // Pivot + relative coordinates can round to opposite sides of a
            // quantization cell. Match spatially and give BOTH copies the same
            // rest point and exactly half weight; a near-half weight still tears.
            float epsilonSquared=.002F*.002F;
            var seam=new ArrayList<Vector3f>();
            for(int i=0;i<a.vertices().length;i+=stride)
            {
                var point=restPoint(a,i);
                for(int j=0;j<b.vertices().length;j+=stride)
                {
                    var other=restPoint(b,j);if(point.distanceSquared(other)>epsilonSquared)continue;
                    var centre=new Vector3f(point).add(other).mul(.5F);
                    if(seam.stream().noneMatch(v->v.distanceSquared(centre)<epsilonSquared))seam.add(centre);
                    break;
                }
            }
            if(seam.size()<3)continue;
            for(String name:new String[]{upper,lower})
            {
                var p=parts.get(name);float[] weights=new float[p.vertices().length/stride],rest=p.vertices().clone();
                for(int i=0;i<weights.length;i++)
                {
                    var point=restPoint(p,i*stride);float distanceSquared=Float.POSITIVE_INFINITY;Vector3f nearest=null;
                    for(var s:seam){float d=point.distanceSquared(s);if(d<distanceSquared){distanceSquared=d;nearest=s;}}
                    if(distanceSquared<epsilonSquared)
                    {
                        weights[i]=.5F;rest[i*stride]=nearest.x-p.pivotX();
                        rest[i*stride+1]=nearest.y-p.pivotY();rest[i*stride+2]=nearest.z-p.pivotZ();
                    }
                    else
                    {
                        float t=Math.max(0,1-(float)Math.sqrt(distanceSquared)/6);weights[i]=.5F*t*t*(3-2*t);
                    }
                }
                result.put(name,new JointSkin(name.equals(upper)?lower:upper,weights,rest,rest.clone()));
            }
            ProjectSeele.LOGGER.info("EVA joint skin seam: joint={} side={} sharedVertices={}",joint,side,seam.size());
        }
        return Map.copyOf(result);
    }

    private static GeoBone findBone(GeoBone bone,String name)
    {
        if(bone.getName().equals(name))return bone;
        for(var child:bone.getChildBones()){var found=findBone(child,name);if(found!=null)return found;}
        return null;
    }

    /** Dual-quaternion blending keeps both copies of every seam vertex coincident. */
    private static float[] skinVertices(MeshData mesh,MeshPart part,GeoBone bone)
    {
        var skin=mesh.joints().get(bone.getName());if(skin==null)return part.vertices();
        var root=bone;while(root.getParent()!=null)root=root.getParent();var other=findBone(root,skin.other());if(other==null)return part.vertices();
        var matrix=EvaRigTransforms.model(bone).invert().mul(EvaRigTransforms.model(other));
        var q=EvaRigTransforms.rotation(matrix);if(q.w<0)q.mul(-1);
        var dual=new org.joml.Quaternionf(matrix.m30(),matrix.m31(),matrix.m32(),0).mul(q).mul(.5F);
        float[] source=skin.rest(),out=skin.scratch();int stride=mesh.stride();
        for(int vertex=0;vertex<skin.weights().length;vertex++)
        {
            float weight=skin.weights()[vertex];if(weight==0)continue;int i=vertex*stride;
            float rx=q.x*weight,ry=q.y*weight,rz=q.z*weight,rw=1-weight+q.w*weight;
            float inv=1F/(float)Math.sqrt(rx*rx+ry*ry+rz*rz+rw*rw);rx*=inv;ry*=inv;rz*=inv;rw*=inv;
            float dx=dual.x*weight*inv,dy=dual.y*weight*inv,dz=dual.z*weight*inv,dw=dual.w*weight*inv;
            float dot=rx*dx+ry*dy+rz*dz+rw*dw;dx-=rx*dot;dy-=ry*dot;dz-=rz*dot;dw-=rw*dot;
            float tx=2*(-dw*rx+dx*rw-dy*rz+dz*ry),ty=2*(-dw*ry+dx*rz+dy*rw-dz*rx),tz=2*(-dw*rz-dx*ry+dy*rx+dz*rw);
            float x=-(source[i]+part.pivotX())/16,y=(source[i+1]+part.pivotY())/16,z=(source[i+2]+part.pivotZ())/16;
            float ax=2*(ry*z-rz*y),ay=2*(rz*x-rx*z),az=2*(rx*y-ry*x);
            out[i]=-(x+rw*ax+ry*az-rz*ay+tx)*16-part.pivotX();
            out[i+1]=(y+rw*ay+rz*ax-rx*az+ty)*16-part.pivotY();out[i+2]=(z+rw*az+rx*ay-ry*ax+tz)*16-part.pivotZ();
            x=-source[i+5];y=source[i+6];z=source[i+7];ax=2*(ry*z-rz*y);ay=2*(rz*x-rx*z);az=2*(rx*y-ry*x);
            out[i+5]=-(x+rw*ax+ry*az-rz*ay);out[i+6]=y+rw*ay+rz*ax-rx*az;out[i+7]=z+rw*az+rx*ay-ry*ax;
        }
        return out;
    }

    private record MeshPart(float pivotX, float pivotY, float pivotZ,
                            float[] vertices, float muzzleX,
                            float muzzleY, float muzzleZ) {}
}
