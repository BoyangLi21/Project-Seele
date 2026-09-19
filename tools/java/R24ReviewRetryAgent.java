import java.lang.instrument.Instrumentation;
import java.nio.file.Path;
import java.util.Set;

/** Re-arm one UI click in our isolated review; never advances a test phase. */
public final class R24ReviewRetryAgent
{
    public static void agentmain(String input, Instrumentation instrumentation) throws Exception
    {
        if (!"r24-staff".equals(System.getProperty("projectseele.regionalBuild"))) throw new IllegalStateException("Not the R24 staff test JVM");
        if (!Set.of("query", "deploy", "cancel", "redeploy", "recover", "close", "close_radio", "timeout").contains(input)) throw new IllegalArgumentException(input);
        for (Class<?> type : instrumentation.getAllLoadedClasses())
        {
            if (!type.getName().equals("com.projectseele.visual.NervStaffR24Review")) continue;
            var field = type.getDeclaredField("world"); field.setAccessible(true);
            Path world = (Path) field.get(null);
            if (world == null || !world.getFileName().toString().equals("SEELE_R24_TV_REVIEW")) throw new IllegalStateException("Wrong review save");
            if ((Boolean) type.getField("finished").get(null)) throw new IllegalStateException("Review already finished");
            if (input.equals("timeout"))
            {
                var age=type.getDeclaredField("age");age.setAccessible(true);age.setInt(null,13999);
                System.out.println("R24 review diagnostic timeout requested; normal server-thread teardown will save the review");return;
            }
            if (!input.equals(type.getField("input").get(null))) throw new IllegalStateException("Review is not waiting on this click");
            @SuppressWarnings("unchecked") Set<String> sent = (Set<String>) type.getField("inputs").get(null);
            System.out.println("R24 UI RETRY observed inputs=" + sent + "; rearm=" + input);
            if (!sent.remove(input)) throw new IllegalStateException("Original UI click was not sent");
            return;
        }
        throw new IllegalStateException("Review class not loaded");
    }
}
