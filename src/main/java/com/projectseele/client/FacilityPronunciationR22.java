package com.projectseele.client;

import java.util.regex.Pattern;

/** Spoken aliases do not change printed station names or route identities. */
public final class FacilityPronunciationR22
{
    private static final Pattern NERV=Pattern.compile("(?i)(?<![a-z])N[\\s.\\-]*E[\\s.\\-]*R[\\s.\\-]*V(?![a-z])");
    private static final Pattern HAN=Pattern.compile("\\p{IsHan}");
    public static String spoken(String text)
    {
        return NERV.matcher(text).replaceAll(HAN.matcher(text).find()?"奈尔夫":"nerve");
    }
    private FacilityPronunciationR22(){}
}
