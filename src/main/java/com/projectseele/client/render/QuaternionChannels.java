package com.projectseele.client.render;

import org.joml.Quaternionf;
import org.joml.Vector3f;

/** Quaternion to Gecko's Rz * Ry * Rx channels, including a vertical Y axis. */
final class QuaternionChannels
{
    static Vector3f euler(Quaternionf q)
    {
        double length=Math.sqrt((double)q.x*q.x+(double)q.y*q.y+(double)q.z*q.z+(double)q.w*q.w);
        if(!(length>0)||!Double.isFinite(length))throw new IllegalArgumentException("Invalid bone quaternion");
        double x=q.x/length,y=q.y/length,z=q.z/length,w=q.w/length;
        double sinY=Math.max(-1,Math.min(1,2*(w*y-z*x)));
        if(Math.abs(sinY)>1-1e-8)
        {
            // At +/-90 degrees the two usual atan2 pairs are both 0/0.
            // Preserve their combined rotation instead of silently returning
            // zero for both channels (the UN thumb lost its opposition here).
            return new Vector3f(0,(float)Math.copySign(Math.PI/2,sinY),
                    (float)Math.atan2(2*(w*z-x*y),1-2*(x*x+z*z)));
        }
        return new Vector3f((float)Math.atan2(2*(w*x+y*z),1-2*(x*x+y*y)),
                (float)Math.asin(sinY),(float)Math.atan2(2*(w*z+x*y),1-2*(y*y+z*z)));
    }
    private QuaternionChannels(){}
}
