using System.Globalization;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

public sealed class PetDrawing : FrameworkElement
{
    public PetDrawing() => RenderOptions.SetBitmapScalingMode(this, BitmapScalingMode.HighQuality);
    public double Time { get; set; }
    private string action = "idle";
    private double started;
    private readonly LuluVideo video = new();
    private int replay;
    private bool bedAnchor;
    private DrawingGroup? lastCharacter;
    private LuluBedScene? roomWalk;
    private double roomWalkTime;
    internal LuluPoseTransition? PoseTransition { get; private set; }
    internal static BitmapSource PoseImage(Action<DrawingContext> draw)
    {
        var visual = new DrawingVisual();
        RenderOptions.SetBitmapScalingMode(visual, BitmapScalingMode.HighQuality);
        using (var dc = visual.RenderOpen()) { dc.PushTransform(new ScaleTransform(2.56, 2.56)); draw(dc); dc.Pop(); }
        var image = new RenderTargetBitmap(512, 512, 96, 96, PixelFormats.Pbgra32); image.Render(visual); image.Freeze(); return image;
    }
    internal void BeginPoseTransition(BitmapSource target, double seconds)
    {
        var source = PoseImage(dc => { if (lastCharacter is not null) dc.DrawDrawing(lastCharacter); else DrawRig(dc); });
        PoseTransition = new(source, target, seconds);
    }
    internal void ClearPoseTransition() => PoseTransition = null;
    internal BitmapSource PrepareRoomWalk()
    {
        roomWalk = new LuluBedScene(); roomWalkTime = .25;
        return PoseImage(dc => roomWalk.DrawApproachPose(dc, roomWalkTime, true));
    }
    internal void AdvanceRoomWalk(double seconds) => roomWalkTime += Math.Max(0, seconds);
    internal BitmapSource PrepareRoomTurn()
    {
        // Use the planted, side-facing pose, then replay the original short turn
        // back to front. Optical flow only joins similarly oriented side poses.
        roomWalk = new LuluBedScene(); roomWalkTime = .75;
        return PoseImage(dc => roomWalk.DrawApproachPose(dc, roomWalkTime, true));
    }
    internal bool AdvanceRoomTurn(double seconds)
    {
        roomWalkTime = Math.Max(.25, roomWalkTime - Math.Max(0, seconds));
        return roomWalkTime <= .25;
    }
    public void RestartAnimation() { started = Time; replay++; }
    internal void ResumeIdleAnimation() { video.ResumeAfterBed(Time); RestartAnimation(); }
    public string Action { get => action; set { if (value != action) { action = value; started = Time; } } }
    public double Phase => Math.Max(0, Time - started);
    public double? PosePhase { get; set; }
    public bool KeepStatePose { get; set; }
    private LuluBedScene? bedScene;
    internal LuluBedScene? BedScene { get => bedScene; set { bedScene = value; if (value is not null) bedAnchor = true; } }
    internal void FinishBedScene() { BedScene = null; video.ResumeAfterBed(Time); }
    internal bool BedApproaching { get; set; }
    public double WalkPhase { get; set; }
    public double LookAway { get; set; }
    public double Squash { get; set; }
    public double EarTwitch { get; set; }
    public string Emotion { get; set; } = "neutral";
    private string wall = "";
    private double wallStarted;
    public string Wall { get => wall; set { if (wall != value) { wall = value; wallStarted = Time; } } }
    public double Reveal { get; set; }
    public bool FacingRight { get; set; } = true;
    public Point Gaze { get; set; }
    public double TalkLevel { get; set; }
    public double Happiness { get; set; } = 75;
    public int Unread { get; set; }
    public string Food { get; set; } = "🍉";
    public static double Duration(string a) => LuluVideo.Duration(a) ?? (a switch { "spin" => 1.4, "roll" => 2.6, "wave" => 2.4, "nod" or "shakeHead" => 1.8, "stretch" => 2.2, "eat" => 3.2, "play" => 6.5, "dance" => 4.2, _ => 4 });
    internal static Brush B(string color) { var b = (SolidColorBrush)new BrushConverter().ConvertFromString(color)!; b.Freeze(); return b; }
    private static double Smooth(double t) { t = Math.Clamp(t, 0, 1); return t * t * (3 - 2 * t); }

    protected override void OnRender(DrawingContext c)
    {
        if (PoseTransition is { } transition)
        {
            double factor = ActualHeight / 200;
            c.PushTransform(new ScaleTransform(factor, factor));
            var pose = new DrawingGroup(); using (var dc = pose.Open()) dc.DrawImage(transition.Frame, new Rect(0, 0, 200, 200));
            pose.Freeze(); lastCharacter = pose; c.DrawDrawing(pose); c.Pop(); return;
        }
        if (BedScene is { } bed)
        {
            // WM_SIZE/layout may still expose the old narrow width on the first
            // render. The pet's scale depends on height; only the scenery expands.
            double factor = ActualHeight / 200;
            c.PushTransform(new TranslateTransform(0, (ActualHeight - 200 * factor) / 2));
            c.PushTransform(new ScaleTransform(factor, factor));
            bed.Draw(c);
            c.Pop(); c.Pop(); return;
        }
        if (Wall.Length > 0) { DrawWall(c); return; }
        double k = Math.Min(ActualWidth, ActualHeight) / 200;
        double offsetX = bedAnchor ? 0 : (ActualWidth - k * 200) / 2;
        if (ActualWidth <= ActualHeight) bedAnchor = false;
        c.PushTransform(new TranslateTransform(offsetX, (ActualHeight - k * 200) / 2));
        c.PushTransform(new ScaleTransform(k, k));
        var character = new DrawingGroup();
        RenderOptions.SetBitmapScalingMode(character, BitmapScalingMode.HighQuality);
        using (var dc = character.Open()) DrawRig(dc);
        // The room walk owns reusable WriteableBitmap frames; do not freeze its
        // live buffer through the drawing group. Capture is performed on this UI thread.
        lastCharacter = character; c.DrawDrawing(character);
        c.Pop(); c.Pop();
    }

    private void DrawRig(DrawingContext c)
    {
        if (BedApproaching && roomWalk is not null) { roomWalk.DrawApproachPose(c, roomWalkTime, true); return; }
        if (video.Draw(c, BedApproaching ? "walk" : Action, Emotion, TalkLevel, Time, PosePhase, replay, FacingRight, KeepStatePose))
        {
            if (Unread > 0)
            {
                var text = new FormattedText(Unread > 99 ? "99+" : Unread.ToString(CultureInfo.InvariantCulture), CultureInfo.InvariantCulture, FlowDirection.LeftToRight, new Typeface("Segoe UI"), 10, Brushes.White, 1);
                c.DrawRoundedRectangle(B("#DA6383"), null, new Rect(139, 109, text.Width + 10, 18), 8, 8); c.DrawText(text, new Point(144, 111));
            }
            return;
        }
        double phase = PosePhase ?? Phase, walk = Action == "walk" ? Math.Sin(WalkPhase) : 0;
        double entry = Smooth(phase / .28), exit = Action is "wave" or "stretch" or "nod" or "shakeHead" ? Smooth((Duration(Action) - phase) / .35) : 1;
        double gesture = entry * exit, bob = Action == "walk" ? -Math.Abs(walk) * 1.3 : 0;
        double lean = 0, headTilt = Math.Clamp(Gaze.X, -4.5, 4.5) * .3;
        double leftArm = 12 - walk * 12, rightArm = -12 - walk * 12;
        double leftFoot = Math.Max(0, walk) * 5, rightFoot = Math.Max(0, -walk) * 5;
        if (Action == "wave") leftArm += gesture * (115 + Math.Sin(phase * 9) * 13);
        if (Action == "stretch") { leftArm += gesture * 140; rightArm -= gesture * 140; headTilt -= gesture * 3; }
        if (Action == "nod") headTilt += Math.Sin(phase * 7) * 5 * gesture;
        if (Action == "shakeHead") headTilt += Math.Sin(phase * 8) * 7 * gesture;
        if (Action == "dance") { lean = Math.Sin(phase * 4) * 5 * entry; leftArm += (40 + Math.Sin(phase * 4) * 18) * entry; rightArm -= (40 - Math.Sin(phase * 4) * 18) * entry; bob -= Math.Abs(Math.Sin(phase * 4)) * 3 * entry; }
        if (Action == "think") { rightArm = -130 * entry; headTilt += 5 * entry; }
        if (Action == "eat") { leftArm = -32 * entry; rightArm = 32 * entry; headTilt += Math.Sin(phase * 5) * 1.5; }
        if (Action == "play") { leftArm = -18; rightArm = 18; headTilt += Math.Sin(phase * 3) * 2; }
        if (Action is "drag" or "fall") { leftArm += 35 * entry; rightArm -= 35 * entry; leftFoot = rightFoot = -2; lean = Math.Sin(Time * 4) * 2; }
        if (Emotion is "curious" or "shy") headTilt += 5;
        if (Emotion == "love") headTilt += Math.Sin(Time * 2) * 3;
        if (Emotion == "sad") headTilt -= 3;
        if (Emotion == "dizzy") headTilt += Math.Sin(Time * 3) * 4;
        double breath = Math.Sin(Time * (Action == "sleep" ? 1.2 : 2)) * .7;
        if (Action == "sleep") { headTilt = 7; leftArm = 5; rightArm = -5; }
        // Keep the feet as the stable anchor; no whole-image squash/stretch.
        c.PushTransform(new TranslateTransform(100, 170));
        c.PushTransform(new ScaleTransform(FacingRight ? 1 : -1, 1));
        c.PushTransform(new RotateTransform(lean));
        c.PushTransform(new TranslateTransform(-100, -170 + bob));
        Joint(c, 4, new Point(80, 151 - leftFoot), walk * -4, new Rect(-11, -2, 23, 22));
        Joint(c, 5, new Point(120, 151 - rightFoot), walk * 4, new Rect(-12, -2, 23, 22));
        LuluRigAssets.Parts.Draw(c, 1, new Rect(63, 91 + breath, 74, 66));
        Joint(c, 3, new Point(132, 103 + breath), rightArm, new Rect(-9, -4, 18, 43));
        Joint(c, 2, new Point(68, 103 + breath), leftArm, new Rect(-9, -4, 18, 43));
        c.PushTransform(new RotateTransform(headTilt, 100, 105 + breath));
        DrawHead(c, new Rect(47, 14 + breath, 106, 99)); c.Pop();
        if (Action == "eat") LuluRigAssets.Parts.Draw(c, 6, new Rect(86, 117 - Math.Sin(phase * 4) * 2, 28, 21));
        if (Action == "play")
        {
            // Analytic parabolic bounce: one persistent ball, no sprite jumps.
            double bounce = (phase * .9) % 1, height = 4 * bounce * (1 - bounce) * 33;
            LuluRigAssets.Parts.Draw(c, 7, new Rect(91, 151 - height, 18, 18));
        }
        if (Unread > 0)
        {
            var text = new FormattedText(Unread > 99 ? "99+" : Unread.ToString(CultureInfo.InvariantCulture), CultureInfo.InvariantCulture, FlowDirection.LeftToRight, new Typeface("Segoe UI"), 10, Brushes.White, 1);
            c.DrawRoundedRectangle(B("#DA6383"), null, new Rect(124, 117, text.Width + 10, 18), 8, 8); c.DrawText(text, new Point(129, 119));
        }
        for (int i = 0; i < 4; i++) c.Pop();
    }

    private static void Joint(DrawingContext c, int part, Point pivot, double angle, Rect bounds)
    {
        c.PushTransform(new TranslateTransform(pivot.X, pivot.Y)); c.PushTransform(new RotateTransform(angle));
        LuluRigAssets.Parts.Draw(c, part, bounds); c.Pop(); c.Pop();
    }
    private void DrawHead(DrawingContext c, Rect bounds)
    {
        if (Action == "sleep") { LuluRigAssets.Faces.Draw(c, 1, bounds); return; }
        if (Action is "drag" or "fall" or "jump") { LuluRigAssets.Faces.Draw(c, 7, bounds); return; }
        int face = Emotion switch { "happy" => 2, "love" => 3, "angry" => 4, "sad" or "sulking" => 5, "shy" => 6, "surprised" => 7, _ => -1 };
        if (face >= 0) { LuluRigAssets.Faces.Draw(c, face, bounds); return; }
        int extra = Emotion switch { "curious" => 0, "sleepy" => 1, "hungry" => 2, "dizzy" => 3, _ => -1 };
        if (extra >= 0) { LuluRigAssets.Extra.Draw(c, extra, bounds); return; }
        LuluRigAssets.Parts.Draw(c, 0, bounds);
    }
    private void DrawWall(DrawingContext c)
    {
        if (LuluEdgeAnimation.Available)
        {
            LuluEdgeAnimation.Draw(c, Wall, Time - wallStarted, Reveal, ActualWidth, ActualHeight);
            return;
        }
        double cutoff = 108 + 68 * Math.Clamp(Reveal, 0, 1.06), h = 132 + 44 * Math.Clamp(Reveal, 0, 1);
        c.PushClip(new RectangleGeometry(new Rect(0, 0, ActualWidth, ActualHeight)));
        c.PushTransform(new ScaleTransform(ActualWidth / (cutoff - 26), ActualHeight / h));
        c.PushTransform(new TranslateTransform(Wall == "left" ? cutoff : -26, 66 + (Wall == "right" ? h - 132 : 0)));
        c.PushTransform(new RotateTransform(Wall == "left" ? 90 : -90)); c.PushTransform(new TranslateTransform(-100, 0));
        DrawRig(c); for (int i = 0; i < 5; i++) c.Pop();
    }
}
