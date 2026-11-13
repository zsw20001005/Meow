namespace Meow.Windows;

public sealed partial class PetWindow
{
    private readonly ConversationPlayback conversationPlayback = new();
    private string heldState = "";
    private bool StateHeld => heldState.Length > 0;
    private static double ExpressionDuration(string emotion) => emotion is "surprised" or "dizzy" ? 5 : emotion is "hungry" or "sleepy" ? 6 : 15;
    internal int ConversationRevision => conversationPlayback.Revision;
    internal string ConversationContext => $"当前动作={pet.Action}，表情={pet.Emotion}，持续保持状态={heldState}，被拖拽或下落={dragging || falling}，动作队列执行中={conversationPlayback.Playing}，最近执行状态={conversationOutcome}。";
    private string conversationOutcome = "没有正在执行的对话动作";
    internal string RunRequestedBehavior(BehaviorReply reply, int revision)
    {
        if (revision != ConversationRevision) return "动作请求已被更新的操作取消。";
        if (dragging || falling) return "当前正在被拖动或下落，站稳后再试这个动作。";
        actionFailure = null;
        ReactToConversation(reply, revision);
        if (actionFailure is not null) return actionFailure;
        var names = reply.Actions.Select(ActionLanguage.Label).ToList();
        if (reply.Emotion != "neutral") names.Add("表情变化");
        return names.Count == 0 ? "这次没有可执行的动作。" : "已开始安排：" + string.Join(" → ", names) + (pet.BedScene?.WakeRequested == true ? "。会先完成起床动画。" : "。");
    }
    private string? actionFailure;
    internal static bool RequiresMotionPack(BehaviorReply reply) => reply.Actions.Append("emotion:" + reply.Emotion).Any(action =>
    {
        string clip = action.StartsWith("emotion:", StringComparison.Ordinal) ? action[8..] : action;
        return LuluVideo.MissingClips.Contains(clip == "sulking" ? "sad" : clip);
    });

    internal void InterruptConversation(bool preserveState = false)
    {
        bool playing = conversationPlayback.Playing || StateHeld;
        if (playing && !preserveState) conversationOutcome = "已被新操作中断";
        conversationPlayback.Interrupt();
        if (preserveState) return;
        heldState = "";
        if (playing && !dragging && !falling) AnimateCore("idle");
    }

    internal void ReactToConversation(BehaviorReply reply, int revision)
    {
        if (StateHeld && !reply.Requested) reply = reply with { Emotion = "neutral", Actions = [], Hold = false };
        if (RequiresMotionPack(reply))
        {
            actionFailure = conversationOutcome = "需要先安装动作表情扩展包；本次动作序列尚未执行。";
            return;
        }
        if (dragging || falling || !conversationPlayback.Start(reply, revision)) return;
        conversationOutcome = "执行中";
        AdvanceConversation();
    }

    private void AdvanceConversation()
    {
        var next = conversationPlayback.Next();
        if (next is "hold" or "free") { Animate(next); conversationOutcome = next == "hold" ? "已处理保持请求" : "已恢复自由活动"; return; }
        bool hold = next is not null && !conversationPlayback.HasPending &&
            (next is "idle" or "walk" or "sleep" || (conversationPlayback.Hold && next.StartsWith("emotion:", StringComparison.Ordinal)));
        AnimateCore(next ?? "idle", speak: false, hold: hold);
        if (next == "idle" && conversationPlayback.HasPending && pet.BedScene is null && !pet.BedApproaching) actionUntil = clock.Elapsed.TotalSeconds + .15;
        if (next is null) { actionUntil = clock.Elapsed.TotalSeconds + 2; conversationOutcome = "本次动作序列已完成"; }
        if (hold) { conversationPlayback.Finish(); conversationOutcome = "正在持续保持，等待新的指令"; }
    }

    private void HoldCurrentState()
    {
        if (dragging || falling || pet.Action is not ("idle" or "walk" or "sleep")) return;
        if (pet.Action == "idle") CancelStroll();
        conversationPlayback.Interrupt();
        heldState = pet.Action == "idle" && pet.Emotion != "neutral" ? "emotion:" + pet.Emotion : pet.Action;
        actionUntil = double.PositiveInfinity;
    }
}
