using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Meow.Windows;

internal sealed record BehaviorReply(string Text, string Emotion, string[] Actions, bool Structured = true, bool Requested = false, bool Hold = false);

internal static class ConversationBehavior
{
    internal static readonly HashSet<string> Actions = ["idle", "wave", "nod", "shakeHead", "stretch", "dance", "roll", "spin", "peek", "walk", "jump", "eat", "play", "sleep", "come", "down", "climb", "hold", "free"];
    internal static readonly HashSet<string> Emotions = ["neutral", "happy", "love", "shy", "curious", "surprised", "angry", "sad", "sleepy", "hungry", "dizzy"];
    internal const string Instructions = """
        本轮你同时为桌面角色选择行为。只返回一个 JSON 对象，text 必须是第一个字段：
        {"text":"自然的中文回复","emotion":"neutral","actions":[],"intent":"reaction","hold":false}
        text 是给主人看的台词，不显示控制数据；不要输出 Markdown 代码块或额外文字。
        emotion 只允许 neutral,happy,love,shy,curious,surprised,angry,sad,sleepy,hungry,dizzy。
        actions 只允许 idle,wave,nod,shakeHead,stretch,dance,roll,spin,peek,walk,jump,eat,play,sleep,come,down,climb,hold,free。
        come=移动到鼠标附近，down=回地面，climb=尝试跳上附近窗口，hold=保持当前状态，free=恢复自由活动。hold/free 只能放最后。
        普通聊天通常 actions=[]、emotion=neutral；根据上下文适度表达，不要每句话都表演。
        intent 只允许 reaction（普通聊天的自然反应）或 request（用户明确要求现在做动作/表情）。普通聊天不能解除已保持的睡觉、站住、散步或表情。
        hold 默认 false；只有用户明确说持续保持某个表情、直到叫停时才设 true，并且 intent=request。只允许保持表情、idle、walk、sleep，不能循环吃瓜、跳跃等一次性动作。
        最后一个动作为 sleep、walk、idle 时会持续保持到用户主动改变，不要再附加表情。普通聊天中没有用户要求停止时，不能用 idle 结束已有状态。
        walk 是走走停停的散步模式：自动交替短时行走和休息，不是一直不停走；无需额外输出 idle 来安排休息。
        动作按顺序播放，最多六个不同动作，随后播放表情；这些是完整角色动画，不能同时叠加。
        分别理解每个分句的否定：“不要睡觉，挥挥手”只挥手；“别睡了，起来挥手”先唤醒再挥手。停止/唤醒的 idle 可以放在序列开头。
        用户说考试通过可开心或挥手；表达喜欢可害羞或喜欢；自然地递来西瓜可 eat；邀请玩球可 play。
        eat/play/sleep/walk/jump/dance/roll/spin 只在用户确实邀请或要求你现在做时选择，不能仅因提及就执行。
        不执行否定、引用、转述、故事、假设或过去发生的动作。不要把用户的难过机械映射为你生气。
        停止用 idle；sleep 必须放最后且 emotion=neutral。不得编造不存在的动作、文件操作或系统指令。
        若本轮已有本地执行的明确口令，则 actions=[]、emotion=neutral，避免重复执行。
        若当前被拖拽或下落则 actions=[]。不要声称已经完成尚未执行的动作，用“好呀，挥挥手～”等回应。
        """;

    private static string Unwrap(string raw)
    {
        raw = raw.TrimStart();
        if (raw.StartsWith('`'))
        {
            int newline = raw.IndexOf('\n');
            if (newline < 0) return "";
            raw = raw[(newline + 1)..].Trim();
            if (raw.EndsWith("```", StringComparison.Ordinal)) raw = raw[..^3].TrimEnd();
        }
        return raw;
    }

    internal static bool HasControlLeak(string text) => Regex.IsMatch(text.Replace("\\\"", "\""), "\"\\s*,\\s*\"(?:emotion|actions|intent|hold|tools)\"\\s*:");

    // Only the first JSON text string is streamed. Partial escapes and metadata never reach the UI.
    internal static string DisplayText(string raw)
    {
        raw = Unwrap(raw);
        if (!raw.StartsWith('{') && !raw.StartsWith('[')) return raw;
        var start = Regex.Match(raw, "^\\{\\s*\"text\"\\s*:\\s*\"");
        if (!start.Success) return "";
        var text = new StringBuilder();
        for (int i = start.Length; i < raw.Length; i++)
        {
            char c = raw[i];
            if (c == '"') break;
            if (c != '\\') { if (c < ' ') break; text.Append(c); continue; }
            if (++i >= raw.Length) break;
            c = raw[i];
            if (c == 'u')
            {
                if (i + 4 >= raw.Length || !ushort.TryParse(raw.AsSpan(i + 1, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture, out var unicode)) break;
                text.Append((char)unicode); i += 4;
            }
            else
            {
                char? decoded = c switch { '"' => '"', '\\' => '\\', '/' => '/', 'n' => '\n', 'r' => '\r', 't' => '\t', 'b' => '\b', 'f' => '\f', _ => null };
                if (!decoded.HasValue) break;
                text.Append(decoded.Value);
            }
        }
        if (text.Length > 0 && char.IsHighSurrogate(text[^1])) text.Length--;
        return text.ToString();
    }

    internal static BehaviorReply Parse(string raw, string userText, bool explicitHandled = false)
    {
        string text = DisplayText(raw);
        try
        {
            using var doc = JsonDocument.Parse(Unwrap(raw));
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("text", out var body) || body.ValueKind != JsonValueKind.String) throw new JsonException();
            text = body.GetString()!;
            if (!root.TryGetProperty("emotion", out var emotion) || emotion.ValueKind != JsonValueKind.String || !Emotions.Contains(emotion.GetString()!) ||
                !root.TryGetProperty("actions", out var actions) || actions.ValueKind != JsonValueKind.Array ||
                actions.GetArrayLength() > 6 || actions.EnumerateArray().Any(a => a.ValueKind != JsonValueKind.String || !Actions.Contains(a.GetString()!))) throw new JsonException();
            // Conservative local guard complements semantic instructions, including model mistakes.
            var filtered = ActionLanguage.Filter(actions.EnumerateArray().Select(a => a.GetString()!).Distinct().ToArray(), userText);
            bool suppress = explicitHandled || ActionLanguage.Narrative(userText) || ActionLanguage.Negative(userText) && filtered.Length == 0;
            var selected = suppress ? [] : filtered;
            int sleep = Array.FindIndex(selected, a => a is "sleep" or "hold" or "free");
            if (sleep >= 0) selected = selected[..(sleep + 1)];
            bool requested = false, hold = false;
            if (root.TryGetProperty("intent", out var intent))
            {
                if (intent.ValueKind != JsonValueKind.String || intent.GetString() is not ("request" or "reaction")) throw new JsonException();
                requested = !suppress && intent.GetString() == "request";
            }
            if (root.TryGetProperty("hold", out var holding))
            {
                if (holding.ValueKind is not (JsonValueKind.True or JsonValueKind.False)) throw new JsonException();
                hold = requested && holding.GetBoolean() && Regex.IsMatch(userText, "保持|一直|持续|直到.*叫停");
            }
            return new(text, suppress || selected.LastOrDefault() is "sleep" or "idle" or "walk" ? "neutral" : emotion.GetString()!, selected, Requested: requested, Hold: hold);
        }
        catch (JsonException) { return new(text, "neutral", [], false); }
    }
}

// A turn can be consumed once. Any new interaction invalidates both its pending steps and late responses.
internal sealed class ConversationPlayback
{
    private readonly Queue<string> pending = new();
    internal int Revision { get; private set; }
    internal bool Playing { get; private set; }
    internal bool HasPending => pending.Count > 0;
    internal bool Hold { get; private set; }
    internal void Interrupt() { Revision++; Finish(); }
    internal void Finish() { pending.Clear(); Playing = false; Hold = false; }
    internal bool Start(BehaviorReply reply, int revision)
    {
        if (Revision != revision) return false;
        Revision++; Finish();
        Hold = reply.Hold;
        foreach (var action in reply.Actions) pending.Enqueue(action);
        if (reply.Emotion != "neutral" && reply.Actions.LastOrDefault() is not ("idle" or "walk" or "sleep")) pending.Enqueue("emotion:" + reply.Emotion);
        Playing = pending.Count > 0;
        return Playing;
    }
    internal string? Next()
    {
        if (pending.TryDequeue(out var action)) return action;
        Playing = false; return null;
    }
}
