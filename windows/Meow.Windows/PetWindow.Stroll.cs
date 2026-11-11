namespace Meow.Windows;

public sealed partial class PetWindow
{
    private string strollPhase = "";
    private double strollElapsed, strollDuration, strollRest;
    private int strollDirection = 1;
    private bool strollRepeats;

    private void CancelStroll()
    {
        if (strollPhase.Length == 0) return;
        strollPhase = ""; pet.PosePhase = null; pet.ClearPoseTransition();
    }

    private System.Windows.Media.Imaging.BitmapSource StrollPose(string action)
        => PetDrawing.PoseImage(dc =>
        {
            if (action == "walk" && strollDirection < 0)
                dc.PushTransform(new System.Windows.Media.ScaleTransform(-1, 1, 100, 100));
            dc.DrawImage(LuluVideo.Frame(action, 0), new System.Windows.Rect(0, 0, 200, 200));
            if (action == "walk" && strollDirection < 0) dc.Pop();
        });

    private void StartStroll(bool repeat, int direction)
    {
        strollRepeats = repeat;
        strollDirection = Left >= Area.Right - Width - 2 ? -1 : Left <= Area.Left + 2 ? 1 : direction;
        // Whole strides finish at the planted pose, rather than stopping mid-step.
        strollDuration = LuluVideo.Duration("walk")!.Value * Random.Shared.Next(4, 7);
        strollElapsed = 0; strollPhase = "starting";
        pet.BeginPoseTransition(StrollPose("walk"), .35);
        pet.Action = "walk"; pet.Emotion = "neutral"; pet.FacingRight = strollDirection > 0;
        pet.PosePhase = 0; velocityX = 0; actionUntil = double.PositiveInfinity;
    }

    private void RestFromStroll(bool repeat)
    {
        strollRepeats = repeat; strollPhase = "stopping"; strollElapsed = 0;
        strollRest = 2.5 + Random.Shared.NextDouble() * 1.5;
        pet.BeginPoseTransition(StrollPose("idle"), .4);
        pet.Action = "idle"; pet.Emotion = "neutral"; pet.PosePhase = 0; velocityX = 0;
    }

    internal bool AdvanceStroll(double seconds)
    {
        if (strollPhase.Length == 0) return false;
        if (dragging || falling) { CancelStroll(); return false; }
        if (pet.PoseTransition is { } transition)
        {
            if (transition.Error is not null)
            {
                CancelStroll(); heldState = "idle"; pet.Action = "idle"; velocityX = 0;
                pet.RestartAnimation(); return true;
            }
            if (!transition.Advance(seconds)) return true;
            pet.ClearPoseTransition(); strollElapsed = 0;
            if (strollPhase == "starting") strollPhase = "walking";
            else if (strollRepeats) strollPhase = "resting";
            else { CancelStroll(); pet.ResumeIdleAnimation(); actionUntil = clock.Elapsed.TotalSeconds + 2; }
            return true; // Present the exact endpoint before advancing its clip.
        }
        if (strollPhase == "resting")
        {
            strollElapsed += seconds; pet.PosePhase = strollElapsed;
            if (strollElapsed >= strollRest) StartStroll(true, strollDirection);
            return true;
        }
        double before = strollElapsed;
        strollElapsed = Math.Min(strollDuration, strollElapsed + Math.Max(0, seconds));
        pet.PosePhase = strollElapsed;
        static double Ease(double t) { t = Math.Clamp(t, 0, 1); return t * t * (3 - 2 * t); }
        // Ease travel speed and brake before an edge; turn only after resting.
        double edgeRoom = strollDirection > 0 ? Area.Right - Width - Left : Left - Area.Left;
        velocityX = strollDirection * 25 * Ease(strollElapsed / .4) * Ease((strollDuration - strollElapsed) / .4)
            * Math.Clamp(edgeRoom / 8, .12, 1);
        Left += velocityX * (strollElapsed - before); Clamp();
        if (strollElapsed >= strollDuration || edgeRoom <= .5) RestFromStroll(strollRepeats);
        return true;
    }
}
