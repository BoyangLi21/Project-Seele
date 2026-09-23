package com.projectseele.util;

import java.lang.ref.ReferenceQueue;
import java.lang.ref.Reference;
import java.lang.ref.WeakReference;
import java.util.HashMap;
import java.util.Objects;
import java.util.function.Function;

/**
 * Small synchronized state table keyed by object identity, without retaining keys.
 * Minecraft Entity equality uses its network ID, which is shared by the client and
 * integrated-server copies. Values must not retain their key, directly or indirectly.
 */
public final class WeakIdentityMap<K,V>
{
    private static final class Key<T> extends WeakReference<T>
    {
        private final int hash;

        Key(T value,ReferenceQueue<T> queue)
        {
            super(Objects.requireNonNull(value,"Weak identity key"),queue);
            hash=System.identityHashCode(value);
        }

        @Override public int hashCode() { return hash; }

        @Override public boolean equals(Object other)
        {
            if(this==other)return true;
            if(!(other instanceof Key<?> key))return false;
            Object value=get();
            return value!=null&&value==key.get();
        }
    }

    private final ReferenceQueue<K> collected=new ReferenceQueue<>();
    private final HashMap<Key<K>,V> values=new HashMap<>();

    private void expunge()
    {
        for(var key=collected.poll();key!=null;key=collected.poll())values.remove(key);
    }

    public synchronized V get(K key)
    {
        expunge();
        try{return values.get(new Key<>(key,null));}
        finally{Reference.reachabilityFence(key);}
    }

    public synchronized V getOrDefault(K key,V fallback)
    {
        V value=get(key);return value==null?fallback:value;
    }

    public synchronized V put(K key,V value)
    {
        expunge();
        try{return values.put(new Key<>(key,collected),Objects.requireNonNull(value,"Weak identity value"));}
        finally{Reference.reachabilityFence(key);}
    }

    public synchronized V remove(K key)
    {
        expunge();
        try{return values.remove(new Key<>(key,null));}
        finally{Reference.reachabilityFence(key);}
    }

    public synchronized V computeIfAbsent(K key,Function<? super K,? extends V> factory)
    {
        Objects.requireNonNull(factory,"State factory");
        V value=get(key);
        if(value==null)
        {
            value=factory.apply(key);
            if(value!=null)put(key,value);
        }
        return value;
    }

    public synchronized int size()
    {
        expunge();return values.size();
    }

    public synchronized void clear()
    {
        values.clear();expunge();
    }
}
