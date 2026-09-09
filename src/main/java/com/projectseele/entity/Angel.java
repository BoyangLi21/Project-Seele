package com.projectseele.entity;

/**
 * Marker for Angel entities. Implementing this is all a new Angel needs to
 * participate in the shared systems (attack alarm now; A.T. Field later).
 */
public interface Angel
{
    /** Remaining field strength, when this Angel has a finite contact barrier. */
    default float getAtField(){return 0;}
}
