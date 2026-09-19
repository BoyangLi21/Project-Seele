package com.projectseele.client;

import java.util.regex.Pattern;

/** Spoken aliases do not change printed station names or route identities. */
public final class FacilityPronunciationR22
{
    private static final Pattern NERV=Pattern.compile("(?i)(?<![a-z])N[\\s.,，·\\-]*E[\\s.,，·\\-]*R[\\s.,，·\\-]*V(?![a-z])");
    private static final Pattern HAN=Pattern.compile("\\p{IsHan}");
    public static String spoken(String text)
    {
        String normalized=java.text.Normalizer.normalize(text,java.text.Normalizer.Form.NFKC);
        return NERV.matcher(normalized).replaceAll(HAN.matcher(normalized).find()?"奈尔夫":"nerve");
    }
    private static final java.util.Set<String> REVIEW_ROWS=new java.util.LinkedHashSet<>();
    public static String spokenFromMtr(String text)
    {
        String result=spoken(text);
        if(System.getProperty("projectseele.regionalBuild","").startsWith("r25-")&&!text.equals(result))
        {
            synchronized(REVIEW_ROWS)
            {
                if(REVIEW_ROWS.size()<64&&REVIEW_ROWS.add(text+" → "+result))
                {
                    try
                    {
                        var path=java.nio.file.Path.of("../artifacts/facility_r25/audio/pronunciation_native.json");
                        java.nio.file.Files.createDirectories(path.getParent());
                        java.nio.file.Files.writeString(path,new com.google.gson.Gson().toJson(REVIEW_ROWS));
                    }
                    catch(java.io.IOException e){throw new IllegalStateException("Native MTR speech witness",e);}
                }
            }
        }
        return result;
    }
    private FacilityPronunciationR22(){}
}
