using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class BedSceneChecks
{
    internal static int ExportSeams()
    {
        var folder = Path.Combine(AppContext.BaseDirectory, "bed-seam-source"); Directory.CreateDirectory(folder);
        var timing = new LuluBedScene();
        double sleep = timing.SleepStarts, wake = sleep + timing.LoopDuration, leave = wake + LuluBedScene.DepartureStart;
        double done = leave + timing.DepartureDuration + LuluBedScene.SettleDuration;
        BitmapSource RenderAt(double time)
        {
            var scene = new LuluBedScene { UseJoins = false }; scene.Advance(sleep); scene.RequestWake();
            if (time < sleep) { scene = new() { UseJoins = false }; scene.Advance(time); } else scene.Advance(time - sleep);
            var drawing = new PetDrawing { Width = 512, Height = 256, BedScene = scene };
            if (time < 0 || scene.Complete) { drawing.FinishBedScene(); drawing.Width = 256; drawing.Action = "idle"; drawing.RestartAnimation(); }
            drawing.Measure(new Size(512, 256)); drawing.Arrange(new Rect(0, 0, drawing.Width, 256));
            var image = new RenderTargetBitmap(512, 256, 96, 96, PixelFormats.Pbgra32); image.Render(drawing); return image;
        }
        foreach (var (name, from, to, seconds) in new[] {
            ("start", -1d, .25, .25), ("approach", 9.8, 10d, .2),
            ("sleep", sleep-.2, sleep, .2), ("breath", wake-.2, sleep, .2),
            ("wake", sleep, wake+.2, .2), ("return", leave-.2, leave, .2),
            ("idle", done-.25, done, .25) })
        {
            foreach (var (side, at) in new[] { ("from", from), ("to", to) })
            { var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(RenderAt(at))); using var f = File.Create(Path.Combine(folder, $"{name}-{side}.png")); png.Save(f); }
            File.WriteAllText(Path.Combine(folder, name+".txt"), seconds.ToString(System.Globalization.CultureInfo.InvariantCulture));
        }
        return 0;
    }
    internal static int RenderFilm(bool walkOnly = false)
    {
        var folder = Path.Combine(AppContext.BaseDirectory, walkOnly ? "bed-walk-frames" : "bed-film-frames"); Directory.CreateDirectory(folder);
        var scene = new LuluBedScene();
        if (walkOnly) { scene.Advance(scene.SleepStarts); scene.RequestWake(); scene.Advance(scene.LoopDuration + 2); }
        var drawing = new PetDrawing { Width = 800, Height = 400, BedScene = scene };
        drawing.Measure(new Size(800, 400)); drawing.Arrange(new Rect(0, 0, 800, 400));
        const double filmFps = 60;
        double duration = (walkOnly ? -2 : scene.SleepStarts + scene.LoopDuration) + LuluBedScene.DepartureStart + scene.DepartureDuration + LuluBedScene.SettleDuration + 3;
        int frameCount = (int)Math.Ceiling(duration * filmFps);
        File.WriteAllText(Path.Combine(folder, "frame-count.txt"), frameCount.ToString(System.Globalization.CultureInfo.InvariantCulture));
        File.WriteAllText(Path.Combine(folder, "frame-rate.txt"), filmFps.ToString(System.Globalization.CultureInfo.InvariantCulture));
        for (int i = 0; i < frameCount; i++)
        {
            if (i > 0) scene.Advance(1 / filmFps);
            if (i / filmFps >= scene.SleepStarts + 2) scene.RequestWake();
            drawing.Time = i / filmFps;
            if (scene.Complete && drawing.BedScene is not null)
            {
                drawing.FinishBedScene(); drawing.Width = 400; drawing.Action = "idle"; drawing.RestartAnimation();
                drawing.Measure(new Size(400, 400)); drawing.Arrange(new Rect(0, 0, 400, 400));
            }
            drawing.InvalidateVisual(); drawing.UpdateLayout();
            var backdrop = new DrawingVisual(); using (var dc = backdrop.RenderOpen()) dc.DrawRectangle(PetDrawing.B("#34475A"), null, new Rect(0, 0, 800, 400));
            var target = new RenderTargetBitmap(800, 400, 96, 96, PixelFormats.Pbgra32); target.Render(backdrop); target.Render(drawing);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(target)); using var output = File.Create(Path.Combine(folder, $"{i:D4}.png")); png.Save(output);
        }
        return 0;
    }
    internal static int Run()
    {
        var output = Path.Combine(AppContext.BaseDirectory, "bed-checks"); Directory.CreateDirectory(output);
        var log = new List<string>();
        void Check(bool ok, string label) { if (!ok) throw new Exception(label); log.Add("PASS " + label); }
        BitmapSource Render(LuluBedScene scene, double factor = 1)
        {
            var drawing = new PetDrawing { Width = 400 * factor, Height = 200 * factor, BedScene = scene };
            drawing.Measure(new Size(drawing.Width, drawing.Height)); drawing.Arrange(new Rect(0, 0, drawing.Width, drawing.Height)); drawing.UpdateLayout();
            var bitmap = new RenderTargetBitmap((int)drawing.Width, (int)drawing.Height, 96, 96, PixelFormats.Pbgra32); bitmap.Render(drawing); return bitmap;
        }
        double Error(BitmapSource a, BitmapSource b)
        {
            int stride = a.PixelWidth * 4; var left = new byte[stride * a.PixelHeight]; var right = new byte[left.Length];
            a.CopyPixels(left, stride, 0); b.CopyPixels(right, stride, 0);
            long sum = 0; int count = 0;
            for (int p = 0; p < left.Length; p += 4) if (left[p + 3] > 24 || right[p + 3] > 24)
                for (int c = 0; c < 4; c++) { sum += Math.Abs(left[p + c] - right[p + c]); count++; }
            return (double)sum / Math.Max(1, count);
        }
        void Save(BitmapSource image, string name) { var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(image)); using var file = File.Create(Path.Combine(output, name + ".png")); png.Save(file); }
        try
        {
            BitmapSource AtSize(PetDrawing drawing, int w, int h)
            {
                drawing.Width = w; drawing.Height = h; drawing.Measure(new Size(w, h)); drawing.Arrange(new Rect(0, 0, w, h)); drawing.InvalidateVisual(); drawing.UpdateLayout();
                var target = new RenderTargetBitmap(w, h, 96, 96, PixelFormats.Pbgra32); target.Render(drawing); return target;
            }
            var resizing = new PetDrawing { BedScene = new LuluBedScene() };
            var beforeExpansion = AtSize(resizing, 200, 200);
            var afterExpansion = new CroppedBitmap(AtSize(resizing, 400, 200), new Int32Rect(0, 0, 200, 200));
            Save(beforeExpansion, "sleep-before-window-resize"); Save(afterExpansion, "sleep-after-window-resize");
            Check(Error(beforeExpansion, afterExpansion) < .01, "sleep character scale and position do not change while window width catches up");
            resizing.FinishBedScene(); resizing.Action = "idle"; resizing.RestartAnimation();
            var beforeContraction = new CroppedBitmap(AtSize(resizing, 400, 200), new Int32Rect(0, 0, 200, 200));
            var afterContraction = AtSize(resizing, 200, 200);
            Check(Error(beforeContraction, afterContraction) < .01, "returning idle stays left-anchored until window contraction completes");
            var empty = new LuluBedScene(); var emptyStart = Render(empty); Save(emptyStart, "starts-without-bed");
            var pixels = new byte[400 * 200 * 4]; emptyStart.CopyPixels(pixels, 1600, 0);
            Check(!Enumerable.Range(0, 200).Any(row => Enumerable.Range(170, 230).Any(col => pixels[(row * 400 + col) * 4 + 3] > 0)), "first frame has no bed anywhere to Lulu's right");
            var arrival = new LuluBedScene(); arrival.Advance(arrival.ArrivalDuration - .000001); var arrivalEnd = Render(arrival); double arrivalCamera = arrival.CameraX; arrival.Advance(.000002);
            BitmapSource Source(double time)
            {
                var visual = new DrawingVisual(); RenderOptions.SetBitmapScalingMode(visual, BitmapScalingMode.HighQuality);
                using (var dc = visual.RenderOpen()) { dc.PushTransform(new TranslateTransform(-arrival.CameraX, 0)); arrival.DrawVideo(dc, "entry", time); dc.Pop(); }
                var image = new RenderTargetBitmap(400, 200, 96, 96, PixelFormats.Pbgra32); image.Render(visual); return image;
            }
            double afterError = Error(Render(arrival), Source(LuluBedScene.ApproachLead + .00001));
            log.Add($"Arrival camera discontinuity: {Math.Abs(arrivalCamera - arrival.CameraX):F6}; source error {afterError:F3}");
            Save(arrivalEnd, "arrival-end"); Save(Source(LuluBedScene.ApproachLead - .00001), "arrival-original");
            Check(arrival.Phase == "entry" && Math.Abs(arrivalCamera - arrival.CameraX) < .01 && afterError < 4, "approach joins entry with continuous camera position");
            var velocity = new LuluBedScene(); velocity.Advance(velocity.ArrivalDuration - .001);
            double ca = velocity.CameraX; velocity.Advance(.001); double cb = velocity.CameraX; velocity.Advance(.001); double cc = velocity.CameraX;
            Check(Math.Abs((cb-ca)/.001 - (cc-cb)/.001) < 3, "approach camera velocity is continuous when walking reaches the bed");
            BitmapSource Feet(LuluBedScene scene) => new CroppedBitmap(Render(scene), new Int32Rect(45, 125, 110, 60));
            var walk = new LuluBedScene(); walk.Advance(1); var feet = Feet(walk); double camera = walk.CameraX, bedWorld = walk.BedWorldX; walk.Advance(.25);
            Check(Error(feet, Feet(walk)) > 2, "feet animate while camera follows rightward approach");
            Check(walk.CameraX > camera && walk.BedWorldX == bedWorld && Math.Abs(walk.BedScreenX + walk.CameraX - bedWorld) < .001, "bed is stationary in world space and enters only because camera moves");
            var uninterrupted = new LuluBedScene(); uninterrupted.Advance(2); var beforeReset = Feet(uninterrupted); uninterrupted.Advance(.5 / 1.35);
            Check(Error(beforeReset, Feet(uninterrupted)) > 2, "walking no longer resets the old accelerated twelve-frame fragment");
            var entry = new LuluBedScene(); entry.Advance(entry.SleepStarts - 1d / 24); var entryLast = Render(entry); entry.Advance(1d / 24 + .00001); var loopFirst = Render(entry);
            double enterError = Error(entryLast, loopFirst); log.Add($"Entry/loop foreground RGBA error: {enterError:F3}/255"); Check(enterError < 12, "entry to loop endpoint difference is bounded (not a motion-quality verdict)");
            var cycle = new LuluBedScene(); cycle.Advance(cycle.SleepStarts + .00001); var cycleStart = Render(cycle); cycle.Advance(2); var cycleMiddle = Render(cycle);
            Check(Error(cycleStart, cycleMiddle) > .25, "real quilt/body pixels move during sleep");
            var wrap = new LuluBedScene(); wrap.Advance(wrap.SleepStarts + wrap.LoopDuration - .000001);
            var wrapLast = Render(wrap); wrap.Advance(.000002); var wrapFirst = Render(wrap);
            Save(wrapLast, "breath-last"); Save(wrapFirst, "breath-first");
            double mouthError = Error(new CroppedBitmap(wrapLast, new Int32Rect(173, 90, 8, 7)), new CroppedBitmap(wrapFirst, new Int32Rect(173, 90, 8, 7)));
            log.Add($"Breath mouth endpoint error: {mouthError:F3}/255");
            Check(mouthError < 10, "breathing loop returns with a closed, matching mouth instead of clipping an open-mouth frame");
            cycle.Advance(60); Check(cycle.Phase == "loop", "sleep stays in breathing loop beyond sixty seconds");
            cycle.RequestWake(); cycle.RequestWake(); double phaseBefore = cycle.Elapsed;
            cycle.Advance(Math.Max(0, cycle.LoopDuration - phaseBefore - .001)); Check(cycle.Phase == "loop", "wake waits for the current breathing cycle endpoint");
            cycle.Advance(.002); Check(cycle.Phase == "wake", "wake begins at the shared sleeping pose");
            cycle.Advance(LuluBedScene.DepartureStart - cycle.Elapsed - .000001); var wakeLast = Render(cycle); camera = cycle.CameraX; cycle.Advance(.000002);
            Check(cycle.Phase == "leave" && Math.Abs(camera - cycle.CameraX) < .01, "wake joins continuing leftward walk with no camera jump");
            var leftFirst = Render(cycle); Save(wakeLast, "wake-last"); Save(leftFirst, "left-first");
            var cadence = new LuluBedScene(); cadence.Advance(cadence.SleepStarts); cadence.RequestWake(); cadence.Advance(cadence.LoopDuration + LuluBedScene.DepartureStart + .000001);
            BitmapSource? priorStep = null; int heldFrames = 0;
            for (int i = 0; i < 60; i++)
            {
                var step = Render(cadence);
                Check(cadence.DisplayedFrame == ("depart", i), $"left walk samples frame {i} at 60 Hz without 24 fps frame holds");
                if (priorStep is not null && Error(new CroppedBitmap(step, new Int32Rect(45, 95, 95, 80)), new CroppedBitmap(priorStep, new Int32Rect(45, 95, 95, 80))) < .05) heldFrames++;
                priorStep = step; cadence.Advance(1d / 60);
            }
            Check(heldFrames == 0 && Math.Abs(cadence.DepartureDuration + LuluBedScene.SettleDuration - 190d / 24) < .00001, "60 fps walking has changing limb images and preserves all 190 source frames of the accepted S14 take");
            Check(Math.Abs(cadence.DepartureDuration - 3.5) < .00001, "S14 bed exit completes before the source begins turning");
            double gaitError = Error(new CroppedBitmap(wakeLast, new Int32Rect(45, 95, 95, 80)), new CroppedBitmap(leftFirst, new Int32Rect(45, 95, 95, 80)));
            log.Add($"Wake/walk arms and feet endpoint error: {gaitError:F3}/255");
            Check(gaitError < 5, "registered wake/walk bridge removes the hard limb-pose cut");
            cycle.Advance(.1); feet = Feet(cycle); camera = cycle.CameraX; cycle.Advance(.25);
            Check(Error(feet, Feet(cycle)) > 2 && cycle.CameraX < camera, "feet keep stepping left while bed recedes to the right");
            cycle.Advance(cycle.DepartureDuration / 2 - cycle.Elapsed);
            var exitPixels = new byte[400 * 200 * 4]; Render(cycle).CopyPixels(exitPixels, 1600, 0);
            Check(!Enumerable.Range(0, 95).Any(row => Enumerable.Range(170, 230).Any(col => exitPixels[(row * 400 + col) * 4 + 3] > 0)), "moving bed layer contains no detached hair or head fragments");
            cycle.Advance(cycle.DepartureDuration - cycle.Elapsed + .00001);
            Check(cycle.Phase == "settle" && cycle.BedScreenX >= 400, "bed has left the viewport before Lulu begins stopping");
            cycle.Advance(LuluBedScene.SettleDuration - cycle.Elapsed + .00001); Check(cycle.Complete, "Lulu finishes original walking-to-standing frames after bed leaves view");
            var terminal = new CroppedBitmap(Render(cycle), new Int32Rect(0, 0, 200, 200));
            var idleDrawing = new PetDrawing { Width = 200, Height = 200, Time = 123.4, Action = "sleep", BedScene = cycle };
            idleDrawing.FinishBedScene(); idleDrawing.Action = "idle"; idleDrawing.RestartAnimation();
            idleDrawing.Measure(new Size(200, 200)); idleDrawing.Arrange(new Rect(0, 0, 200, 200));
            var idleStart = new RenderTargetBitmap(200, 200, 96, 96, PixelFormats.Pbgra32); idleStart.Render(idleDrawing);
            Save(terminal, "terminal-pose"); Save(idleStart, "real-idle-handoff");
            log.Add($"Exit/actual idle foreground error: {Error(terminal, idleStart):F3}/255");
            Check(Error(terminal, idleStart) < 2.5, "standing exit reaches actual idle geometry rather than a similar generated pose");
            var sheet = new DrawingVisual();
            using (var dc = sheet.RenderOpen())
            {
                dc.DrawRectangle(PetDrawing.B("#34475A"), null, new Rect(0, 0, 1200, 600));
                double[] samples = [0, 2, arrival.ArrivalDuration, arrival.ArrivalDuration + 4, entry.SleepStarts, entry.SleepStarts + 2];
                for (int i = 0; i < samples.Length; i++) { var s = new LuluBedScene(); s.Advance(samples[i]); dc.DrawImage(Render(s), new Rect(i % 3 * 400, i / 3 * 200, 400, 200)); }
                dc.DrawImage(wakeLast, new Rect(0, 400, 400, 200)); dc.DrawImage(Render(cycle), new Rect(400, 400, 400, 200));
                var sleeping = new LuluBedScene(); sleeping.Advance(sleeping.SleepStarts + 2); dc.DrawImage(Render(sleeping), new Rect(800, 400, 400, 200));
                Save(Render(sleeping, .92), "desktop-size");
            }
            var target = new RenderTargetBitmap(1200, 600, 96, 96, PixelFormats.Pbgra32); target.Render(sheet); Save(target, "sequence");
            log.Add("Source caveats: slight model shape/tail variation remains; numerical checks do not certify natural motion.");
            return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); return 1; }
        finally { File.WriteAllLines(Path.Combine(output, "results.txt"), log); }
    }
}
