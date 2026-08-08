package com.projectseele.world;

import com.projectseele.entity.EvaScale;
import com.projectseele.entity.EvaUnit01Entity;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/**
 * Single coordinate authority for the canonical entry-plug and dorsal socket.
 *
 * <p>Plug frame P: +X right, +Y hatch/top, +Z from insertion tip toward the
 * occupied body, and -Z insertion. Socket frame S uses the same axes with +Z
 * pointing out of the EVA's back. Every marker and route is expressed in one
 * of these two frames; no screen-space yaw/pitch patches belong here.</p>
 */
public final class EntryPlugKinematics
{
    public static final double MODEL_TO_BLOCK =
            EvaScale.ENTRY_PLUG_RENDER_SCALE / 16.0D;
    public static final double LOCK_DEPTH_BLOCKS = 5.4D;
    public static final double DOCK_PHASE_END = 0.45D;
    public static final double ALIGN_PHASE_END = 0.75D;
    public static final float HATCH_OPEN_TRAVEL_MODEL = 4.6F;

    public static final Vec3 BODY_OBB_CENTRE_P =
            new Vec3(0.0D, 0.0D, 5.0D);
    public static final Vec3 BODY_OBB_HALF_EXTENTS =
            new Vec3(1.0D, 1.0D, 5.0D);
    public static final Vec3 HATCH_PORTAL_HALF_EXTENTS_P =
            modelMarker(2.5D, 0.4D, 7.0D);
    public static final Vec3 HATCH_PORTAL_CENTRE_P =
            modelMarker(0.0D, 4.0D, 29.0D);
    public static final Vec3 PILOT_SEAT_P =
            modelMarker(0.0D, -2.0D, 31.0D);
    public static final Vec3 PILOT_EYE_P =
            modelMarker(0.0D, 0.8D, 27.5D);
    /**
     * The seated pilot looks out through the hatch/top face.  The former
     * {@code -Z_P} view followed the capsule's long axis; while the plug was
     * hanging vertically that forced the pilot to stare at the floor and made
     * the otherwise-correct crane rotation read as if it were upside down.
     */
    public static final Vec3 PILOT_VIEW_FORWARD_P =
            new Vec3(0.0D, 1.0D, 0.0D);
    public static final Vec3 PILOT_DISMOUNT_LEFT_P =
            modelMarker(-6.4D, 5.2D, 29.0D);
    public static final Vec3 PILOT_DISMOUNT_RIGHT_P =
            modelMarker(6.4D, 5.2D, 29.0D);
    /** Crane eye at the capsule tail, opposite the lower insertion tip. */
    public static final Vec3 CRANE_ATTACHMENT_P =
            modelMarker(0.0D, 0.0D, 50.0D);

    /*
     * The reviewed Tiger meshes are 192 model units high at a 5/16
     * block-per-unit render scale. The dorsal opening is on the upper-back
     * torso at approximately y=145 and z=+12.8 model units.
     */
    public static final double SOCKET_HEIGHT_BLOCKS = 50.5D;
    public static final double SOCKET_REAR_BLOCKS = 4.8D;
    private static final Vec3 WORLD_UP = new Vec3(0.0D, 1.0D, 0.0D);
    /** Entry channel rises 60 degrees behind the upright airframe. */
    private static final double SOCKET_REAR_AXIS = 0.5D;
    private static final double SOCKET_UP_AXIS =
            0.8660254037844386D;

    private EntryPlugKinematics() {}

    public static RigidTransform socketTransform(EvaUnit01Entity unit)
    {
        Vec3 rear = unit.getRearDirection();
        Vec3 outward = rear.scale(SOCKET_REAR_AXIS)
                .add(WORLD_UP.scale(SOCKET_UP_AXIS)).normalize();
        // Keep plug +Y on the dorsal/hatch side while +Z follows the sloped
        // spinal channel. Deriving all three orthogonal axes avoids the shear
        // produced by pairing a tilted Z axis with raw WORLD_UP.
        Vec3 hatchSide = rear.subtract(
                outward.scale(rear.dot(outward))).normalize();
        Vec3 right = hatchSide.cross(outward).normalize();
        Vec3 origin = unit.position()
                .add(rear.scale(SOCKET_REAR_BLOCKS))
                .add(0.0D, SOCKET_HEIGHT_BLOCKS, 0.0D);
        return RigidTransform.fromAxes(
                origin, right, hatchSide, outward);
    }

    /**
     * Authored cage pose whose hatch marker, not entity centre, lands at the
     * boarding point. The insertion tip is the lowest point under the crane
     * and the capsule rises above it; its +Y hatch face looks toward the rear
     * boarding bridge.
     */
    public static RigidTransform dockTransform(EvaUnit01Entity unit,
                                                Vec3 hatchCentreWorld)
    {
        return dockTransform(hatchCentreWorld, unit.getRearDirection());
    }

    /**
     * Authored wet-cage dock.  Unlike the compatibility overload above this
     * frame does not read the airframe's live head/body interpolation.  The
     * crane, bridge and pressure hatch are civil works fixed at the reviewed
     * silo yaw, so allowing even a fraction of a degree of entity yaw into
     * this transform makes a parked capsule visibly roll around its cable.
     */
    public static RigidTransform cageDockTransform(Vec3 hatchCentreWorld)
    {
        return dockTransform(hatchCentreWorld,
                rearDirectionForYaw(EvaUnit01Entity.SILO_BAY_YAW));
    }

    private static RigidTransform dockTransform(Vec3 hatchCentreWorld,
                                                 Vec3 hatchFacing)
    {
        Vec3 normalizedFacing = hatchFacing.multiply(1.0D, 0.0D, 1.0D)
                .normalize();
        // x = y cross z keeps the authored plug frame right-handed while
        // +Z points from the lower insertion tip up through the capsule.
        Vec3 right = normalizedFacing.cross(WORLD_UP).normalize();
        RigidTransform orientation = RigidTransform.fromAxes(
                Vec3.ZERO, right, normalizedFacing, WORLD_UP);
        Vec3 tip = hatchCentreWorld.subtract(
                orientation.transformVector(HATCH_PORTAL_CENTRE_P));
        return new RigidTransform(tip,
                orientation.qx(), orientation.qy(),
                orientation.qz(), orientation.qw());
    }

    /**
     * Evaluates the complete SUSPENDED -> APPROACH -> MOUTH -> LOCKED route.
     * Translation and rotation are both authored in socket space.
     */
    public static RigidTransform insertionTransform(
            EvaUnit01Entity unit, Vec3 hatchCentreWorld, double progress)
    {
        return insertionTransform(unit,
                dockTransform(unit, hatchCentreWorld), progress);
    }

    /**
     * Evaluates insertion from an already-authoritative world-space dock.
     * Wet-cage logistics uses {@link #cageDockTransform(Vec3)} here so the
     * start frame cannot be re-parented to a moving EVA before socket lock.
     */
    public static RigidTransform insertionTransform(
            EvaUnit01Entity unit, RigidTransform dockWorld, double progress)
    {
        double linear = Mth.clamp(progress, 0.0D, 1.0D);
        RigidTransform socket = socketTransform(unit);
        RigidTransform dockInSocket = socket.inverse().compose(
                dockWorld);
        RigidTransform approachInSocket = new RigidTransform(
                new Vec3(0.0D, 5.0D, 8.4D),
                0.0F, 0.0F, 0.0F, 1.0F);
        RigidTransform mouthInSocket = RigidTransform.identity();
        RigidTransform plugInSocket;
        if (linear <= DOCK_PHASE_END)
        {
            double phase = smoothstep(linear / DOCK_PHASE_END);
            plugInSocket = dockInSocket.interpolate(
                    approachInSocket, phase);
        }
        else if (linear <= ALIGN_PHASE_END)
        {
            double phase = smoothstep((linear - DOCK_PHASE_END)
                    / (ALIGN_PHASE_END - DOCK_PHASE_END));
            plugInSocket = approachInSocket.interpolate(
                    mouthInSocket, phase);
        }
        else
        {
            double phase = smoothstep((linear - ALIGN_PHASE_END)
                    / (1.0D - ALIGN_PHASE_END));
            plugInSocket = new RigidTransform(
                    new Vec3(0.0D, 0.0D,
                            -LOCK_DEPTH_BLOCKS * phase),
                    0.0F, 0.0F, 0.0F, 1.0F);
        }
        return socket.compose(plugInSocket);
    }

    /** Horizontal rear vector matching vanilla yaw without reading an entity. */
    private static Vec3 rearDirectionForYaw(float yawDegrees)
    {
        double yaw = Math.toRadians(yawDegrees);
        return new Vec3(Math.sin(yaw), 0.0D, -Math.cos(yaw)).normalize();
    }

    public static RigidTransform lockedTransform(EvaUnit01Entity unit)
    {
        return socketTransform(unit).compose(new RigidTransform(
                new Vec3(0.0D, 0.0D, -LOCK_DEPTH_BLOCKS),
                0.0F, 0.0F, 0.0F, 1.0F));
    }

    /**
     * Conservative world AABB of one oriented local-space box. The renderer
     * still uses the exact quaternion; this envelope exists only for server
     * interlocks and deliberately errs on the side of stopping machinery.
     */
    public static AABB worldBounds(RigidTransform transform, Vec3 centre,
                                   Vec3 halfExtents)
    {
        double minX = Double.POSITIVE_INFINITY;
        double minY = Double.POSITIVE_INFINITY;
        double minZ = Double.POSITIVE_INFINITY;
        double maxX = Double.NEGATIVE_INFINITY;
        double maxY = Double.NEGATIVE_INFINITY;
        double maxZ = Double.NEGATIVE_INFINITY;
        for (int sx : new int[] {-1, 1})
        {
            for (int sy : new int[] {-1, 1})
            {
                for (int sz : new int[] {-1, 1})
                {
                    Vec3 corner = transform.transformPoint(centre.add(
                            halfExtents.x * sx, halfExtents.y * sy,
                            halfExtents.z * sz));
                    minX = Math.min(minX, corner.x);
                    minY = Math.min(minY, corner.y);
                    minZ = Math.min(minZ, corner.z);
                    maxX = Math.max(maxX, corner.x);
                    maxY = Math.max(maxY, corner.y);
                    maxZ = Math.max(maxZ, corner.z);
                }
            }
        }
        return new AABB(minX, minY, minZ, maxX, maxY, maxZ);
    }

    /** Samples rotation as well as translation, so a turning capsule cannot
     * cut a corner outside the two endpoint AABBs. */
    public static AABB sweptBodyBounds(RigidTransform from,
                                       RigidTransform to)
    {
        AABB sweep = worldBounds(from, BODY_OBB_CENTRE_P,
                BODY_OBB_HALF_EXTENTS);
        for (int sample = 1; sample <= 4; sample++)
        {
            RigidTransform pose = from.interpolate(to, sample / 4.0D);
            sweep = sweep.minmax(worldBounds(pose, BODY_OBB_CENTRE_P,
                    BODY_OBB_HALF_EXTENTS));
        }
        return sweep;
    }

    /** Both pressure-door leaves travel laterally by this distance. */
    public static AABB hatchClosingSweep(RigidTransform transform)
    {
        double travel = HATCH_OPEN_TRAVEL_MODEL * MODEL_TO_BLOCK;
        Vec3 expanded = new Vec3(
                HATCH_PORTAL_HALF_EXTENTS_P.x + travel,
                HATCH_PORTAL_HALF_EXTENTS_P.y,
                HATCH_PORTAL_HALF_EXTENTS_P.z);
        return worldBounds(transform, HATCH_PORTAL_CENTRE_P, expanded);
    }

    private static Vec3 modelMarker(double x, double y, double z)
    {
        return new Vec3(x * MODEL_TO_BLOCK,
                y * MODEL_TO_BLOCK, z * MODEL_TO_BLOCK);
    }

    private static double smoothstep(double value)
    {
        double clamped = Mth.clamp(value, 0.0D, 1.0D);
        return clamped * clamped * (3.0D - 2.0D * clamped);
    }
}
