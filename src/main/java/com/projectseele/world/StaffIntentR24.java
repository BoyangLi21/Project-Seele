package com.projectseele.world;

import java.text.Normalizer;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;

/** A bounded command vocabulary; questions and ambiguous requests never press controls. */
public final class StaffIntentR24
{
    public enum Kind { TOPIC, QUERY, ACTION, CANCEL, INVALID }
    public record Intent(Kind kind, String subject, int unit)
    {
        public boolean mutates() { return kind == Kind.ACTION || kind == Kind.CANCEL; }
    }

    private static final Pattern UNIT = Pattern.compile(
            "(?<![A-Z0-9])(?:EVA[-_ ]?|UNIT[-_ ]?)?(0[012]|[012])(?![A-Z0-9])(?:号机)?|([零初一壹二贰貳])号(?:机)?");
    private static final Pattern QUESTION = Pattern.compile("吗|么|能否|是否|可否|可以|能不能|怎么|怎样|如何|为什么|[?？]");
    private static final Pattern NEGATIVE = Pattern.compile("不要|别|不许|禁止");
    private static final Pattern AMBIGUOUS = Pattern.compile("或者|还是|同时|分别|[;；\\n\\r]|\\bOR\\b");
    private static final Pattern POLITE = Pattern.compile("^(?:(?:请帮我|请你|请|帮我|麻烦你|麻烦|把|将)\\s*)+");
    private static final Map<String, String> ACTIONS = Map.ofEntries(
            Map.entry("整备", "prepare"), Map.entry("准备", "prepare"), Map.entry("PREPARE", "prepare"),
            Map.entry("发射", "launch"), Map.entry("出击", "launch"), Map.entry("LAUNCH", "launch"),
            Map.entry("回收", "recover"), Map.entry("RECOVER", "recover"),
            Map.entry("准备并发射", "deploy"), Map.entry("整备并发射", "deploy"),
            Map.entry("准备后发射", "deploy"), Map.entry("整备后发射", "deploy"),
            Map.entry("准备并出击", "deploy"), Map.entry("整备并出击", "deploy"));

    public static Intent parse(String input)
    {
        if (input == null || input.length() > 160)
        {
            return new Intent(Kind.INVALID, "请使用简短、明确的指令。", -1);
        }
        String text = Normalizer.normalize(input, Normalizer.Form.NFKC).strip().toUpperCase(Locale.ROOT)
                .replace('號', '号').replace('機', '机').replace('發', '发').replace('備', '备').replace('擊', '击');
        text = text.replaceFirst("^(?:美里|律子|冬月(?:司令)?|司令)[,，:：]\\s*", "");
        if (text.isBlank()) return new Intent(Kind.TOPIC, "greeting", -1);
        if (text.startsWith("TOPIC:"))
        {
            String topic = text.substring(6).toLowerCase(Locale.ROOT);
            if (java.util.Set.of("greeting", "status", "readiness", "directions", "city", "sync", "plug", "power", "duty", "campaign").contains(topic))
                return new Intent(Kind.TOPIC, topic, -1);
            return new Intent(Kind.INVALID, "没有这个交谈主题。", -1);
        }
        if (AMBIGUOUS.matcher(text).find())
            return new Intent(Kind.INVALID, "请一次指定一台机体和一个明确流程。", -1);

        var units = UNIT.matcher(text);
        int unit = -1, count = 0;
        while (units.find())
        {
            count++;
            unit = units.group(1) != null ? Integer.parseInt(units.group(1))
                    : switch (units.group(2)) { case "零" -> 0; case "初", "一", "壹" -> 1; default -> 2; };
        }
        if (count > 1) return new Intent(Kind.INVALID, "请只指定一台机体。", -1);
        boolean operation = text.matches(".*(?:整备|准备|发射|出击|回收|PREPARE|LAUNCH|RECOVER).*" );
        if (QUESTION.matcher(text).find() && (operation || text.matches(".*(?:取消|停止|中止).*")))
            return new Intent(Kind.QUERY, operation ? "readiness" : "status", unit);
        if (NEGATIVE.matcher(text).find() && text.matches(".*(?:取消|停止).*"))
            return new Intent(Kind.INVALID, "这句话有多重否定，请明确选择继续还是取消。", unit);
        if (text.matches(".*(?:取消|停止|中止).*" ) || NEGATIVE.matcher(text).find() && operation)
            return new Intent(Kind.CANCEL, "cancel", unit);
        if (NEGATIVE.matcher(text).find())
            return new Intent(Kind.INVALID, "收到，不执行动作。", unit);

        String body = UNIT.matcher(text).replaceAll("").strip();
        body = POLITE.matcher(body).replaceFirst("").replaceAll("[\\s,，]+", "")
                .replaceFirst("(?:一下|吧|。|!|！)+$", "");
        String action = ACTIONS.get(body);
        if (action != null)
            return unit >= 0 ? new Intent(Kind.ACTION, action, unit)
                    : new Intent(Kind.INVALID, "请指定零号机、初号机或二号机。", -1);
        if (operation) return new Intent(Kind.INVALID, "可用指令：整备、发射、回收，或整备后发射，并指定机体。", unit);
        if (text.matches(".*(?:车站|火车|机库|指挥室|观察廊|钢琴|指路|路线|怎么走).*"))
            return new Intent(Kind.TOPIC, "directions", unit);
        if (text.matches(".*(?:战况|状态|现在|进度).*")) return new Intent(Kind.TOPIC, "status", unit);
        if (text.matches(".*(?:任务|剧情|作战记录|使徒).*")) return new Intent(Kind.TOPIC, "campaign", unit);
        if (text.contains("同步")) return new Intent(Kind.TOPIC, "sync", unit);
        if (text.contains("插入栓")) return new Intent(Kind.TOPIC, "plug", unit);
        if (text.matches(".*(?:供电|能源|电缆).*")) return new Intent(Kind.TOPIC, "power", unit);
        if (text.matches(".*(?:城市|东京|NERV|奈尔夫).*")) return new Intent(Kind.TOPIC, "city", unit);
        if (text.matches(".*(?:工作|值班|休息|辛苦).*")) return new Intent(Kind.TOPIC, "duty", unit);
        return new Intent(Kind.TOPIC, "greeting", unit);
    }

    private StaffIntentR24() {}
}
