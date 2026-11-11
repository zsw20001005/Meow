namespace Meow.Windows;

public sealed partial class PetWindow
{
    private readonly ConversationPlayback conversationPlayback = new();
    private string heldState = "";
    private bool StateHeld => heldState.Length > 0;
    private static double ExpressionDuration(string emotion) => emotion is "surprised" or "dizzy" ? 5 : emotion is "hungry" or "sleepy" ? 6 : 15;
    internal int ConversationRevision => conversationPlayback.Revision;
    internal string ConversationContext => $"当前动作={pet.Action}，表情={pet.Emotion}，持续保持状态={heldState}，被拖拽或下落={dragging || falling}。";

    internal void InterruptConversation(bool preserveState = false)
    {
        bool playing = conversationPlayback.Playing || StateHeld;
        conversationPlayback.Interrupt();
        if (preserveState) return;
        heldState = "";
        if (playing && !dragging && !falling) AnimateCore("idle");
    }

    internal void ReactToConversation(BehaviorReply reply, int revision)
    {
        if (StateHeld && !reply.Requested) reply = reply with { Emotion = "neutral", Actions = [], Hold = false };
        if (dragging || falling || !conversationPlayback.Start(reply, revision)) return;
        AdvanceConversation();
    }

    private void AdvanceConversation()
    {
        var next = conversationPlayback.Next();
        bool hold = next is not null && !conversationPlayback.HasPending &&
            (next is "idle" or "walk" or "sleep" || (conversationPlayback.Hold && next.StartsWith("emotion:", StringComparison.Ordinal)));
        AnimateCore(next ?? "idle", speak: false, hold: hold);
        if (next is null) actionUntil = clock.Elapsed.TotalSeconds + 2;
        if (hold) conversationPlayback.Finish();
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
