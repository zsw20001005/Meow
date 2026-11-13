namespace Meow.Windows;

public sealed partial class PetWindow
{
    private (string Action, bool Speak, bool Hold) afterBed = ("idle", false, true);
    private double roomStart, roomTarget, roomElapsed, roomDuration;
    private bool roomTurning, roomTurnComplete;
    private void BeginBedEntry()
    {
        var scene = new LuluBedScene { UseJoins = false };
        scene.Advance(.25); // Replace the fixed idle-zero bridge, not the walking take.
        var target = PetDrawing.PoseImage(scene.Draw);
        scene.UseJoins = true;
        pet.BeginPoseTransition(target, .5);
        pet.BedApproaching = false; Width = Height * 2; pet.BedScene = scene;
    }
    private bool TryBedAction(string action, bool speak, bool hold)
    {
        if (pet.BedApproaching)
        {
            if (action == "sleep") return true;
            pet.BedApproaching = false;
            pet.ClearPoseTransition();
        }
        if (pet.BedScene is { } scene)
        {
            if (action == "sleep" && scene.Phase is "arrive" or "entry" or "loop") scene.KeepSleeping();
            else { afterBed = (action, speak, hold); scene.RequestWake(); }
            heldState = "sleep"; actionUntil = double.PositiveInfinity;
            return true;
        }
        if (action != "sleep" || !LuluBedScene.Available || dragging || falling) return false;
        ReleaseWall(); platform = jumpTarget = IntPtr.Zero; velocityX = velocityY = 0;
        // Keep the requested left-to-right choreography even near the screen edge.
        // Walk to a roomy starting position first instead of mirroring or teleporting.
        if (Left + Height * 2 > Area.Right)
        {
            roomTurning = roomTurnComplete = false;
            var target = pet.PrepareRoomWalk();
            pet.BeginPoseTransition(target, .6);
            pet.BedApproaching = true; pet.FacingRight = false;
            roomStart = Left; roomTarget = Math.Max(Area.Left, Area.Right - Height * 2); roomElapsed = 0;
            roomDuration = Math.Max(.6, (roomStart - roomTarget) / 60 + .4);
        }
        else BeginBedEntry();
        pet.Action = "sleep"; pet.Emotion = "neutral";
        heldState = "sleep"; actionUntil = double.PositiveInfinity;
        afterBed = ("idle", false, true);
        return true;
    }

    private void CancelBedScene()
    {
        pet.BedApproaching = false;
        pet.ClearPoseTransition();
        if (pet.BedScene is null) return;
        pet.BedScene = null; Width = Height;
        Clamp();
    }

    internal bool AdvanceBedScene(double seconds)
    {
        if ((pet.BedApproaching || pet.BedScene is not null) && pet.PoseTransition is { } transition)
        {
            if (transition.Error is not null)
            {
                CancelBedScene(); heldState = ""; AnimateCore("idle", false, true); Say("动作过渡准备失败了，可以再试一次。"); return false;
            }
            if (!transition.Advance(seconds)) return true;
            pet.ClearPoseTransition();
            return true; // Display the exact target before advancing its source clip.
        }
        if (pet.BedApproaching)
        {
            if (roomTurning)
            {
                // Render the final original turn frame before capturing the
                // next bridge; lastCharacter is updated by the render pass.
                if (roomTurnComplete) BeginBedEntry();
                else roomTurnComplete = pet.AdvanceRoomTurn(seconds);
                return true;
            }
            roomElapsed += Math.Max(0, seconds);
            pet.AdvanceRoomWalk(seconds);
            double t = Math.Clamp(roomElapsed / roomDuration, 0, 1);
            Left = roomStart + (roomTarget - roomStart) * t * t * (3 - 2 * t);
            pet.WalkPhase += seconds * 6;
            if (t >= 1)
            {
                var target = pet.PrepareRoomTurn();
                pet.BeginPoseTransition(target, .25);
                roomTurning = true;
            }
            return true;
        }
        if (pet.BedScene is not { } scene) return false;
        scene.Advance(seconds);
        if (!scene.Complete) return true;
        var next = afterBed; pet.FinishBedScene(); Width = Height; Clamp(); heldState = "";
        AnimateCore(next.Action, next.Speak, next.Hold);
        if (next.Action == "idle" && !next.Hold && conversationPlayback.HasPending) actionUntil = clock.Elapsed.TotalSeconds + .15;
        return pet.BedScene is not null;
    }
}
