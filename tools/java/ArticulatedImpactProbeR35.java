import com.bulletphysics.collision.broadphase.*;
import com.bulletphysics.collision.dispatch.*;
import com.bulletphysics.collision.shapes.*;
import com.bulletphysics.dynamics.*;
import com.bulletphysics.dynamics.constraintsolver.*;
import com.bulletphysics.linearmath.*;
import com.google.gson.*;
import javax.vecmath.*;
import java.nio.file.*;
import java.util.*;

/** Isolated Java engine proof. It never opens or edits a Minecraft world. */
public final class ArticulatedImpactProbeR35 {
    static Transform transform(JsonArray values){float[] a=new float[16];for(int i=0;i<16;i++)a[i]=values.get(i).getAsFloat();return new Transform(new Matrix4f(a));}
    static Vector3f vec(JsonArray a){return new Vector3f(a.get(0).getAsFloat(),a.get(1).getAsFloat(),a.get(2).getAsFloat());}
    static JsonArray matrix(Transform t){Matrix4f m=new Matrix4f();t.getMatrix(m);JsonArray a=new JsonArray();for(int row=0;row<4;row++)for(int col=0;col<4;col++)a.add(m.getElement(row,col));return a;}
    static RigidBody body(float mass,CollisionShape shape,Transform at,DiscreteDynamicsWorld world){Vector3f inertia=new Vector3f();if(mass>0)shape.calculateLocalInertia(mass,inertia);RigidBodyConstructionInfo info=new RigidBodyConstructionInfo(mass,new DefaultMotionState(at),shape,inertia);info.friction=.85f;info.restitution=0;info.linearDamping=.10f;info.angularDamping=.68f;RigidBody b=new RigidBody(info);world.addRigidBody(b);return b;}
    public static void main(String[] args)throws Exception{
        JsonObject definition=JsonParser.parseString(Files.readString(Path.of(args[0]))).getAsJsonObject();
        DefaultCollisionConfiguration config=new DefaultCollisionConfiguration();CollisionDispatcher dispatcher=new CollisionDispatcher(config);
        DiscreteDynamicsWorld world=new DiscreteDynamicsWorld(dispatcher,new DbvtBroadphase(),new SequentialImpulseConstraintSolver(),config);world.setGravity(new Vector3f(0,-9.81f,0));world.getSolverInfo().numIterations=30;
        Transform floor=new Transform();floor.setIdentity();body(0,new StaticPlaneShape(new Vector3f(0,1,0),0),floor,world);
        Map<String,RigidBody> bodies=new LinkedHashMap<>();Map<String,Transform> binds=new LinkedHashMap<>();Map<String,Transform> initials=new LinkedHashMap<>();
        Map<String,HingeConstraint> hinges=new LinkedHashMap<>();
        for(JsonElement element:definition.getAsJsonArray("bodies")){
            JsonObject row=element.getAsJsonObject();String n=row.get("name").getAsString();var size=row.getAsJsonArray("size");
            CollisionShape shape=row.get("shape").getAsString().equals("box")?new BoxShape(vec(size)):new CapsuleShape(size.get(0).getAsFloat(),Math.max(.01f,size.get(1).getAsFloat()));shape.setMargin(.004f);
            if(row.has("hulls")&&!row.getAsJsonArray("hulls").isEmpty()){
                CompoundShape compound=new CompoundShape();Transform identity=new Transform();identity.setIdentity();
                for(var hull:row.getAsJsonArray("hulls")){var points=new com.bulletphysics.util.ObjectArrayList<Vector3f>();for(var point:hull.getAsJsonArray())points.add(vec(point.getAsJsonArray()));ConvexHullShape convex=new ConvexHullShape(points);convex.setMargin(.003f);compound.addChildShape(identity,convex);}shape=compound;
            }
            Transform bind=transform(row.getAsJsonArray("bind"));binds.put(n,bind);initials.put(n,transform(row.getAsJsonArray("initial")));RigidBody b=body(row.get("mass").getAsFloat(),shape,bind,world);b.setActivationState(4);b.setCcdMotionThreshold(.03f);b.setCcdSweptSphereRadius(.025f);bodies.put(n,b);
        }
        for(JsonElement element:definition.getAsJsonArray("bodies")){
            JsonObject row=element.getAsJsonObject();if(row.get("parent").isJsonNull())continue;String n=row.get("name").getAsString(),parent=row.get("parent").getAsString();
            Transform joint=transform(row.getAsJsonArray("joint"));Transform a=new Transform(binds.get(parent));a.inverse();a.mul(joint);Transform b=new Transform(binds.get(n));b.inverse();b.mul(joint);
            TypedConstraint constraint;
            if(row.has("hinge")){HingeConstraint h=new HingeConstraint(bodies.get(parent),bodies.get(n),a,b);JsonArray limits=row.getAsJsonArray("hinge");h.setLimit(-limits.get(1).getAsFloat(),-limits.get(0).getAsFloat(),.9f,.3f,1);constraint=h;hinges.put(n,h);}
            else{ConeTwistConstraint c=new ConeTwistConstraint(bodies.get(parent),bodies.get(n),a,b);var cone=row.getAsJsonArray("cone");c.setLimit(cone.get(0).getAsFloat(),cone.get(1).getAsFloat(),cone.get(2).getAsFloat());constraint=c;}
            world.addConstraint(constraint,true);
        }
        for(String n:bodies.keySet()){RigidBody b=bodies.get(n);b.setCenterOfMassTransform(initials.get(n));b.setInterpolationWorldTransform(initials.get(n));b.getMotionState().setWorldTransform(initials.get(n));}
        for(var entry:hinges.entrySet())System.out.println(entry.getKey()+" initial hinge "+entry.getValue().getHingeAngle());
        JsonArray frames=new JsonArray();Vector3f impulse=args.length>2&&args[2].equals("side")?new Vector3f(65,0,0):new Vector3f(0,0,65);
        bodies.get("torso_upper").applyCentralImpulse(impulse);
        for(int tick=0;tick<=240;tick++){
            if(tick>0)world.stepSimulation(1f/60,4,1f/240);
            JsonObject frame=new JsonObject();frame.addProperty("time",tick/60.0);JsonObject poses=new JsonObject();
            for(String n:bodies.keySet()){Transform t=bodies.get(n).getCenterOfMassTransform(new Transform());Transform inverse=new Transform(binds.get(n));inverse.inverse();t.mul(inverse);poses.add(n,matrix(t));}frame.add("deformation",poses);
            JsonArray contacts=new JsonArray();for(int i=0;i<dispatcher.getNumManifolds();i++){var m=dispatcher.getManifoldByIndexInternal(i);if(m.getNumContacts()>0)contacts.add(m.getNumContacts());}frame.add("contacts",contacts);frames.add(frame);
        }
        JsonObject output=new JsonObject();output.addProperty("engine","JBullet 1.0.3; constrained articulated dynamics, y-up");output.addProperty("synthetic_root_rotation",false);output.add("frames",frames);Files.writeString(Path.of(args[1]),new Gson().toJson(output));System.out.println("Simulated "+frames.size()+" frames with "+bodies.size()+" linked bodies");
    }
}
