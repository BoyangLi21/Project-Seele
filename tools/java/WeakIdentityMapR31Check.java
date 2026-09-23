import com.projectseele.util.WeakIdentityMap;
import java.lang.ref.WeakReference;
import java.util.concurrent.atomic.AtomicInteger;

/** Pure-Java check; no Minecraft classes or game process are loaded. */
public final class WeakIdentityMapR31Check
{
    private static final class EntityId
    {
        final int id;
        EntityId(int id){this.id=id;}
        @Override public int hashCode(){return id;}
        @Override public boolean equals(Object other){return other instanceof EntityId e&&e.id==id;}
    }
    private static void check(boolean condition,String message)
    {if(!condition)throw new AssertionError(message);}

    private static WeakReference<EntityId> temporary(WeakIdentityMap<EntityId,String> map)
    {
        var key=new EntityId(99);map.put(key,"temporary");return new WeakReference<>(key);
    }

    public static void main(String[] arguments)throws Exception
    {
        var map=new WeakIdentityMap<EntityId,String>();var server=new EntityId(42);var client=new EntityId(42);
        check(server!=client&&server.equals(client),"Fixture must share equals/id but not identity");
        map.put(server,"server-thrown");map.put(client,"client-landed");
        check(map.size()==2,"Equal network IDs must occupy independent slots");
        check("server-thrown".equals(map.get(server)),"Client receive must not replace server reaction");
        check("client-landed".equals(map.get(client)),"Client reaction remains independent");
        map.remove(client);check("server-thrown".equals(map.get(server)),"Client reset must not remove server state");
        check(map.get(new EntityId(42))==null,"An equal ID is not the same live instance");
        var calls=new AtomicInteger();
        map.computeIfAbsent(server,key->{calls.incrementAndGet();return "wrong";});
        map.computeIfAbsent(client,key->{calls.incrementAndGet();return "client-recreated";});
        check(calls.get()==1,"Factory only runs for the missing identity");
        check("fallback".equals(map.getOrDefault(new EntityId(42),"fallback")),"Fallback lookup uses identity");
        var weak=temporary(map);
        for(int i=0;i<30&&weak.get()!=null;i++){System.gc();Thread.sleep(10);}
        if(weak.get()!=null)throw new AssertionError("Temporary entity was retained by the map");
        check(map.size()==2,"Collected keys must be expunged through ReferenceQueue");
        System.out.println("PASS: equal-ID server/client isolation, reset isolation, factories, weak-key collection");
    }
}
