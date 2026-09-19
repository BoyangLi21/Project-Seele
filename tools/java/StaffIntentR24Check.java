import com.projectseele.world.StaffIntentR24;

/** Real utterances that previously risked accidental or ambiguous button presses. */
public final class StaffIntentR24Check
{
    private static int checks;
    private static void check(String text, StaffIntentR24.Kind kind, String subject, int unit)
    {
        var actual = StaffIntentR24.parse(text);
        if (actual.kind() != kind || !actual.subject().equals(subject) || actual.unit() != unit)
            throw new AssertionError(text + " => " + actual);
        checks++;
    }
    private static void noAction(String text)
    {
        if (StaffIntentR24.parse(text).kind() == StaffIntentR24.Kind.ACTION)
            throw new AssertionError("Unexpected operation: " + text);
        checks++;
    }
    public static void main(String[] args)
    {
        var action = StaffIntentR24.Kind.ACTION;
        check("请帮我整备初号机", action, "prepare", 1);
        check("初号机，准备后发射", action, "deploy", 1);
        check("美里，请把 EVA-01 整备并发射。", action, "deploy", 1);
        check("發射零號機", action, "launch", 0);
        check("回收二号机吧。", action, "recover", 2);
        check("LAUNCH UNIT01", action, "launch", 1);
        check("能发射初号机吗？", StaffIntentR24.Kind.QUERY, "readiness", 1);
        check("取消操作了吗？", StaffIntentR24.Kind.QUERY, "status", -1);
        check("不要发射初号机", StaffIntentR24.Kind.CANCEL, "cancel", 1);
        check("取消当前操作", StaffIntentR24.Kind.CANCEL, "cancel", -1);
        check("机库怎么走", StaffIntentR24.Kind.TOPIC, "directions", -1);
        check("TOPIC:campaign", StaffIntentR24.Kind.TOPIC, "campaign", -1);
        for (String text : new String[]{"发射01还是02", "发射所有机体", "不要取消发射01", "发射01;回收02",
                "发射01\n停止操作", "准备发射01", "能不能准备并发射01", "发射 EVA-UN-00", "发射03", "先准备，发射初号机"})
            noAction(text);
        System.out.println("Staff intent checks passed: " + checks);
    }
}
