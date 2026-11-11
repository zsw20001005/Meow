using System.Windows;
namespace Meow.Windows;

public sealed partial class PetWindow
{
    private IntPtr platform;
    private IntPtr jumpTarget;
    private double jumpLandingAt;
    private double platformRefresh, mailNotice, nextStroke, nightWake;
    private double wallReveal;
    private int lastUnread;
    private Rect Area => Desktop.WorkArea(this);
    private bool Docked => store.Data.WallSide.Length > 0;
    private void DockIfNearEdge()
    {
        var a = Area;
        if (Left < a.Left + 20) store.Data.WallSide = "left"; else if (Left + Width > a.Right - 20) store.Data.WallSide = "right"; else store.Data.WallSide = "";
        if (Docked) { falling = false; platform = IntPtr.Zero; velocityX = velocityY = 0; pet.Action = "idle"; pet.ClearPoseTransition(); }
        Save();
    }
    private void ReleaseWall() { store.Data.WallSide = ""; pet.Wall = ""; wallReveal = 0; Width = Height = 230 * store.Data.Scale; Clamp(); }
    private void JumpToWindow()
    {
        if (pet.BedScene is not null) { Animate("climb"); return; }
        InterruptConversation();
        ReleaseWall(); var target = Desktop.Platforms(this).Where(p => p.Bounds.Top > Area.Top + Height * .55).OrderBy(p => Math.Abs(p.Bounds.Left + p.Bounds.Width / 2 - (Left + Width / 2))).FirstOrDefault();
        if (target.Id == IntPtr.Zero) { Say("附近没有适合站的小窗台。"); return; }
        platform = IntPtr.Zero; jumpTarget = target.Id; const double duration = .7;
        double targetX = Math.Clamp(Left, target.Bounds.Left, Math.Max(target.Bounds.Left, target.Bounds.Right - Width));
        double targetY = target.Bounds.Top - Height * .85;
        velocityX = (targetX - Left) / duration; velocityY = (targetY - Top - .5 * 1400 * duration * duration) / duration;
        jumpLandingAt = clock.Elapsed.TotalSeconds + duration; falling = true; pet.Action = "jump"; Say("嘿咻，跳上来啦！");
    }
    private void FeatureFrame(double now, double dt)
    {
        if (jumpTarget != IntPtr.Zero && now >= jumpLandingAt && !dragging)
        {
            var target = Desktop.Platforms(this).FirstOrDefault(p => p.Id == jumpTarget); jumpTarget = IntPtr.Zero;
            if (target.Id != IntPtr.Zero) { platform = target.Id; Left = Math.Clamp(Left, target.Bounds.Left, Math.Max(target.Bounds.Left, target.Bounds.Right - Width)); Top = target.Bounds.Top - Height * .85; falling = false; velocityX = velocityY = 0; pet.Action = "idle"; }
        }
        pet.Unread = Mailbox.Unread;
        if (Mailbox.Unread > lastUnread && now > mailNotice && !Features.ChatBusy && now > bubbleUntil && pet.Action != "sleep") { Say("主人，来信啦！双击我打开信箱看看 💌"); mailNotice = now + 30; lastUnread = Mailbox.Unread; }
        if (Mailbox.Unread < lastUnread) lastUnread = Mailbox.Unread;
        if (Docked && !dragging)
        {
            var pointer = CursorPosition(); var a = Area; bool nearby = Math.Abs(pointer.Y - (Top + Height * .65)) < 100 && (store.Data.WallSide == "left" ? pointer.X < a.Left + 100 : pointer.X > a.Right - 100);
            double target = nearby || Mailbox.Unread > 0 ? 1 : 0; wallReveal += (target - wallReveal) * Math.Min(1, dt * 8); pet.Wall = store.Data.WallSide;
            pet.Reveal = wallReveal; double k = 230 * store.Data.Scale / 200;
            Width = Math.Ceiling((LuluEdgeAnimation.Available ? LuluEdgeAnimation.ViewWidth : 82 + 68 * wallReveal) * k);
            Height = Math.Ceiling((LuluEdgeAnimation.Available ? LuluEdgeAnimation.ViewHeight : 132 + 44 * wallReveal) * k);
            Left = store.Data.WallSide == "left" ? a.Left : a.Right - Width; Top = Math.Clamp(Top, a.Top, Math.Max(a.Top, a.Bottom - Height));
            if (nearby && now > nextStroke && wallReveal > .8) { Say("主人，我在这里陪你呀～"); nextStroke = now + 30; }
        }
        if (platform != IntPtr.Zero && now > platformRefresh && !dragging)
        {
            platformRefresh = now + .2; var target = Desktop.Platforms(this).FirstOrDefault(p => p.Id == platform);
            if (target.Id == IntPtr.Zero || Left + Width * .7 < target.Bounds.Left || Left + Width * .3 > target.Bounds.Right) { platform = IntPtr.Zero; falling = true; }
            else Top = target.Bounds.Top - Height * .85;
        }
        if (!StateHeld && pet.Action == "idle" && now > actionUntil && store.Data.NightSleep && DateTime.Now.Hour is >= 23 or < 7 && now > nightWake && !Features.ChatBusy && !conversationPlayback.Playing && !dragging && !falling) { AnimateCore("sleep", speak: false, hold: true); }
        if (!StateHeld && store.Data.WindowJump && !conversationPlayback.Playing && !Features.ChatBusy && !Docked && platform == IntPtr.Zero && pet.Action == "walk" && now > nextDecision - 1 && Random.Shared.Next(1000) < 2) JumpToWindow();
    }
}
