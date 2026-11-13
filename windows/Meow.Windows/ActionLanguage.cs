using System.Text.RegularExpressions;

namespace Meow.Windows;

internal static class ActionLanguage
{
    internal static bool Narrative(string text) => Regex.IsMatch(text, "故事|小说|台词|举例|翻译|引用|假如|如果|他说|她说|它说|他们说|昨天|曾经|梦见|[“”「」『』\"]");
    internal static bool Negative(string text) => Regex.IsMatch(text, "不要|不许|不用|无需|(?:^|[，。！？、\\s]|请|先|你|噜噜|还是|就|千万|可)别(?!人|的)");
    internal static string Normalize(string text)
    {
        text = text.Trim().TrimEnd('。', '！', '!', '～', '~', '？', '?');
        text = Regex.Replace(text, @"^(?:(?:张噜噜|噜噜|小喵)[，,\s]*|请|你|能不能|能否|可以|帮我|给我|先|再|然后|接着|最后)+", "");
        return Regex.Replace(text, "(?:好不好|可以吗|好吗|给我看|一下吧|吧|呀|啦|嘛|吗)$", m => m.Value == "一下吧" ? "一下" : "");
    }
    internal static BehaviorReply? LocalPlan(string text)
    {
        if (Narrative(text)) return null;
        text = Regex.Replace(text, "(醒醒|起床|起来)(?=挥|转|跳|点|摇|伸|吃|玩|散|走|笑|打|过|下)", "$1，");
        var clauses = Regex.Split(text, "[，,。；;！!]|然后|接着|并且|最后|再(?=挥|转|跳|点|摇|伸|睡|吃|玩|散|走|笑|打|过|下)");
        var actions = new List<string>(); string emotion = "neutral";
        foreach (var raw in clauses)
        {
            var clause = raw.Trim(); if (clause.Length == 0 || Normalize(clause).Length == 0) continue;
            var action = Commands.Action(clause);
            if (action is null)
            {
                if (Negative(clause) && Commands.Action(Regex.Replace(clause, "不要|不许|不用|无需|别", "")) is not null) continue;
                return null;
            }
            if (action.StartsWith("emotion:")) emotion = action[8..];
            else actions.Add(action);
        }
        if (actions.Count > 6 || actions.Count == 0 && emotion == "neutral") return null;
        // Persistent states and controls are terminal; do not pretend later steps ran.
        if (actions.Take(Math.Max(0, actions.Count-1)).Any(a => a is "sleep" or "hold" or "free")) return null;
        return new("", emotion, actions.Distinct().ToArray(), Requested: true);
    }
    internal static string[] Filter(string[] actions, string input)
    {
        if (Narrative(input)) return [];
        if (!Negative(input)) return actions;
        var local = LocalPlan(input);
        if (local is not null) return local.Actions;
        // Negation belongs to its clause. Require a recognized positive action
        // before allowing any model actions from an otherwise negative request.
        return Regex.Split(input, "[，,。；;！!]|然后|接着").Where(c => !Negative(c)).Select(Commands.Action).Where(a => a is not null && actions.Contains(a)).Cast<string>().Distinct().ToArray();
    }
    internal static string Label(string name) => name switch
    {
        "idle" => "停下/唤醒", "wave" => "挥手", "nod" => "点头", "shakeHead" => "摇头", "stretch" => "伸懒腰",
        "dance" => "跳舞", "roll" => "打滚", "spin" => "转圈", "peek" => "张望", "walk" => "散步", "jump" => "跳跃",
        "eat" => "吃西瓜", "play" => "玩球", "sleep" => "睡觉", "come" => "过来", "down" => "下来", "climb" => "跳上窗口",
        "hold" => "保持当前状态", "free" => "恢复自由活动", _ => "表情"
    };
}
