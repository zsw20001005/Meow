using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class AnimationChecks
{
    internal static int Run()
    {
        var output = Path.Combine(AppContext.BaseDirectory, "animation-checks"); Directory.CreateDirectory(output);
        var log = new List<string>();
        try
        {
            string[] required = ["idle", "walk", "wave", "eat", "play", "sleep", "spin", "roll", "stretch", "dance", "nod", "shakeHead", "think", "talk", "peek", "drag", "fall", "land", "jump", "happy", "love", "shy", "curious", "surprised", "angry", "sad", "sleepy", "hungry", "dizzy"];
            var sheet = new Canvas { Width = 1380, Height = 5 * 250, Background = new SolidColorBrush(Color.FromRgb(40, 57, 73)) };
            for (int i = 0; i < required.Length; i++)
            {
                string key = required[i];
                if (!LuluVideo.Clips.TryGetValue(key, out var clip)) throw new Exception("Missing animation: " + key);
                if (clip.Fps != (key == "walk" ? 60 : 24) || clip.Frames < 1 || Math.Abs(PetDrawing.Duration(key) - clip.Frames / clip.Fps) > .0001) throw new Exception("Invalid timing: " + key);
                if (clip.Mode == "hold" && LuluVideo.FrameIndex(clip, 100) != clip.Frames - 1) throw new Exception("One-shot unexpectedly loops: " + key);
                if (clip.Mode == "still" && LuluVideo.FrameIndex(clip, 0) != LuluVideo.FrameIndex(clip, 100)) throw new Exception("Falling pose moves before physical landing");
                var sample = LuluVideo.Frame(key, Math.Min(1.8, clip.Frames / 48d));
                var bgra = new FormatConvertedBitmap(sample, PixelFormats.Bgra32, null, 0);
                int size = LuluVideo.CellSize;
                var pixels = new byte[size * size * 4]; bgra.CopyPixels(pixels, size * 4, 0);
                int clear = 0, opaque = 0;
                for (int p = 3; p < pixels.Length; p += 4) { if (pixels[p] < 8) clear++; if (pixels[p] > 230) opaque++; }
                if (clear < size * size * .24 || opaque < size * size * .015) throw new Exception("Broken transparency/empty character: " + key);
                // Seek the final frame too, ensuring the packed atlas contains the whole clip.
                _ = LuluVideo.Frame(key, (clip.Frames - 1) / clip.Fps);
                for (int page = LuluVideo.PageFrames; page < clip.Frames; page += LuluVideo.PageFrames)
                {
                    _ = LuluVideo.Frame(key, (page - 1) / clip.Fps);
                    var first = LuluVideo.Frame(key, page / clip.Fps);
                    if (first.PixelWidth != size || first.PixelHeight != size) throw new Exception("Invalid page boundary: " + key);
                }
                var image = new Image { Width = 230, Height = 230, Source = sample };
                Canvas.SetLeft(image, i % 6 * 230); Canvas.SetTop(image, i / 6 * 250); sheet.Children.Add(image);
                var label = new TextBlock { Text = key, Foreground = Brushes.White, FontSize = 12 };
                Canvas.SetLeft(label, i % 6 * 230 + 8); Canvas.SetTop(label, i / 6 * 250 + 229); sheet.Children.Add(label);
                log.Add($"PASS {key}: {clip.Frames} frames at {clip.Fps} fps, alpha and last-frame decode");
            }
            sheet.Measure(new Size(sheet.Width, sheet.Height)); sheet.Arrange(new Rect(0, 0, sheet.Width, sheet.Height)); sheet.UpdateLayout();
            var target = new RenderTargetBitmap((int)sheet.Width, (int)sheet.Height, 96, 96, PixelFormats.Pbgra32); target.Render(sheet);
            var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(target));
            using (var file = File.Create(Path.Combine(output, "runtime-states.png"))) png.Save(file);
            CheckTransitions(output, log);
            CheckWalkCycle(output, log);
            foreach (var emotion in ConversationBehavior.Emotions.Where(e => e != "neutral").Concat(new[] { "think" }))
            {
                var held = new LuluVideo(); var visual = new DrawingVisual();
                using (var c = visual.RenderOpen()) held.Draw(c, emotion is "sleep" or "think" ? emotion : "idle", emotion, 0, 60, null, 0, true, true);
                var expected = new DrawingVisual();
                using (var c = expected.RenderOpen()) c.DrawImage(LuluVideo.Frame(emotion, LuluVideo.StatePoseTime(emotion, 60)), new Rect(0, 0, 200, 200));
                if (!Render(visual).SequenceEqual(Render(expected))) throw new Exception("Expression did not retain reviewed pose: " + emotion);
            }
            log.Add("PASS all ten expressions and thinking stay on reviewed poses at 60 seconds instead of relaxing to neutral.");
            CheckSleepCycle(output, log);
            log.Add("PASS runtime timing, bounded atlas cache, transparent WPF state sheet. Visual source issues remain documented.");
            File.WriteAllLines(Path.Combine(output, "results.txt"), log); return 0;
        }
        catch (Exception error) { log.Add("FAIL " + error); File.WriteAllLines(Path.Combine(output, "results.txt"), log); return 1; }
    }

    private static byte[] Render(DrawingVisual visual)
    {
        var bitmap = new RenderTargetBitmap(200, 200, 96, 96, PixelFormats.Pbgra32); bitmap.Render(visual);
        var pixels = new byte[200 * 200 * 4]; bitmap.CopyPixels(pixels, 200 * 4, 0); return pixels;
    }

    private static void CheckWalkCycle(string output, List<string> log)
    {
        var clip = LuluVideo.Clips["walk"];
        var poses = new List<byte[]>();
        for (int i = 0; i < clip.Frames; i++)
        {
            int size = LuluVideo.CellSize;
            var p = new byte[size * size * 4]; LuluVideo.Frame("walk", i / clip.Fps).CopyPixels(p, size * 4, 0); poses.Add(p);
        }
        double Error(byte[] a, byte[] b)
        {
            long error = 0; int count = 0;
            for (int p = 0; p < a.Length; p += 4)
                if (Math.Max(a[p + 3], b[p + 3]) > 32)
                    for (int c = 0; c < 4; c++) { error += Math.Abs(a[p + c] - b[p + c]); count++; }
            return (double)error / count;
        }
        var differences = Enumerable.Range(0, clip.Frames).Select(i => Error(poses[i], poses[(i + 1) % clip.Frames])).ToArray();
        if (differences.Any(e => e < .01)) throw new Exception("Walking repeats an identical frame or endpoint");
        var sorted = differences.Order().ToArray();
        if (differences[^1] > sorted[(int)(sorted.Length * .95)] * 1.25)
            throw new Exception("Walking wrap is an outlier compared with normal steps");
        for (int i = 0; i < clip.Frames * 120; i++)
        {
            double seconds = i / clip.Fps;
            if (LuluVideo.FrameIndex(clip, seconds) != i % clip.Frames) throw new Exception("Walking skips/repeats a frame at a cycle boundary");
            if (!ReferenceEquals(LuluVideo.Frame("walk", seconds), LuluVideo.Frame("walk", (i % clip.Frames) / clip.Fps)))
                throw new Exception("Walking decodes or allocates new frames on repeat");
        }
        log.Add($"PASS walk: 120 cycles, no skipped/duplicate frames, cached decoded frames; wrap difference {differences[^1]:F3}, P95 {sorted[(int)(sorted.Length * .95)]:F3}/255");
        string frames = Path.Combine(output, "walk-loop-frames"); Directory.CreateDirectory(frames);
        var right = new LuluVideo(); var left = new LuluVideo();
        for (int i = 0; i < clip.Frames * 10; i++)
        {
            var visual = new DrawingVisual(); using (var dc = visual.RenderOpen())
            {
                dc.DrawRectangle(Brushes.DarkSlateGray, null, new Rect(0, 0, 512, 256));
                dc.PushTransform(new ScaleTransform(1.28, 1.28));
                right.Draw(dc, "walk", "neutral", 0, i / clip.Fps, null, 0, true, true);
                dc.PushTransform(new TranslateTransform(200, 0));
                left.Draw(dc, "walk", "neutral", 0, i / clip.Fps, null, 0, false, true);
                dc.Pop(); dc.Pop();
            }
            var capture = new RenderTargetBitmap(512, 256, 96, 96, PixelFormats.Pbgra32); capture.Render(visual);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(capture));
            using var file = File.Create(Path.Combine(frames, $"{i:D4}.png")); encoder.Save(file);
        }
        File.WriteAllText(Path.Combine(frames, "frame-count.txt"), (clip.Frames * 10).ToString());
        File.WriteAllText(Path.Combine(frames, "frame-rate.txt"), clip.Fps.ToString(System.Globalization.CultureInfo.InvariantCulture));
        log.Add("PASS exported 10 continuous walking cycles in both directions through the actual player");
    }

    private static void CheckSleepCycle(string output, List<string> log)
    {
        var player = new LuluVideo(); var visual = new DrawingVisual();
        byte[] Sleep(double time)
        {
            using (var c = visual.RenderOpen()) player.Draw(c, "sleep", "neutral", 0, time, null, 0, true, true);
            return Render(visual);
        }
        double entry = LuluVideo.SleepLoopEntry, period = LuluVideo.SleepCycleSeconds;
        var first = Sleep(entry);
        var middle = Sleep(entry + period / 2);
        if (first.SequenceEqual(middle)) throw new Exception("Sleep is frozen instead of breathing");
        // Test actual PetDrawing layout at the user's 80% size, not only byte inequality.
        var pet = new PetDrawing { Width = 184, Height = 184, KeepStatePose = true, Action = "sleep" };
        (int Top, int Bottom) Bounds(double time)
        {
            pet.Time = time; pet.InvalidateVisual();
            pet.Measure(new Size(184, 184)); pet.Arrange(new Rect(0, 0, 184, 184)); pet.UpdateLayout();
            var bitmap = new RenderTargetBitmap(184, 184, 96, 96, PixelFormats.Pbgra32); bitmap.Render(pet);
            var pixels = new byte[184 * 184 * 4]; bitmap.CopyPixels(pixels, 184 * 4, 0);
            int top = 184, bottom = 0;
            for (int y = 0; y < 184; y++)
                for (int x = 0; x < 184; x++)
                    if (pixels[(y * 184 + x) * 4 + 3] > 180) { top = Math.Min(top, y); bottom = Math.Max(bottom, y); }
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(bitmap));
            using (var file = File.Create(Path.Combine(output, time == entry ? "sleep-inhale-80.png" : "sleep-exhale-80.png"))) encoder.Save(file);
            return (top, bottom);
        }
        var inhale = Bounds(entry); var exhale = Bounds(entry + period / 2);
        int movement = exhale.Top - inhale.Top;
        if (movement < 4 || movement > 8 || Math.Abs(inhale.Bottom - exhale.Bottom) > 1)
            throw new Exception($"Sleep is not perceptible/anchored at 80% size: head={movement}px, feet={exhale.Bottom - inhale.Bottom}px");
        log.Add($"PASS actual PetDrawing at 80% scale: {movement}px head rise/fall, feet stable within one pixel.");
        if (!first.SequenceEqual(Sleep(entry + period))) throw new Exception("Sleep cycle does not close seamlessly");
        for (int i = 0; i <= 3600; i++)
        {
            double time = entry + i / 60d, source = LuluVideo.StatePoseTime("sleep", time);
            if (source < 1.75 - .00001 || source > entry + .00001) throw new Exception("Sleep reaches wake-up footage");
            if (i > 0 && Math.Abs(source - LuluVideo.StatePoseTime("sleep", time - 1d / 60)) > 1d / 24) throw new Exception("Sleep source timeline jumps");
        }
        // A manual action immediately removes the breathing transform.
        using (var c = visual.RenderOpen()) player.Draw(c, "wave", "neutral", 0, 100, null, 1, true, true);
        var expected = new DrawingVisual();
        using (var c = expected.RenderOpen()) c.DrawImage(LuluVideo.Frame("wave", 0), new Rect(0, 0, 200, 200));
        if (!Render(visual).SequenceEqual(Render(expected))) throw new Exception("Sleep transform leaks into next action");

        var strip = new DrawingVisual();
        using (var c = strip.RenderOpen())
        {
            for (int i = 0; i < 5; i++)
            {
                var sample = new DrawingVisual(); var sleeper = new LuluVideo();
                using (var s = sample.RenderOpen()) sleeper.Draw(s, "sleep", "neutral", 0, entry + i * period / 4, null, 0, true, true);
                var image = new RenderTargetBitmap(200, 200, 96, 96, PixelFormats.Pbgra32); image.Render(sample);
                c.DrawRectangle(Brushes.DarkSlateGray, null, new Rect(i * 200, 0, 200, 200));
                c.DrawImage(image, new Rect(i * 200, 0, 200, 200));
            }
        }
        var capture = new RenderTargetBitmap(1000, 200, 96, 96, PixelFormats.Pbgra32); capture.Render(strip);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(capture));
        using (var file = File.Create(Path.Combine(output, "sleep-breath-cycle.png"))) encoder.Save(file);
        log.Add("PASS sleep breathes, closes its 4.8s cycle, stays within closed-eye frames for 60s and stops immediately on a new action.");
    }

    private static void CheckTransitions(string output, List<string> log)
    {
        var player = new LuluVideo(); var visual = new DrawingVisual();
        using (var c = visual.RenderOpen()) player.Draw(c, "idle", "neutral", 0, 0, null, 0, true);
        var sheet = new DrawingVisual();
        using (var strip = sheet.RenderOpen())
        {
            int column = 0;
            foreach (double elapsed in new[] { 0d, .025, .06, .10, .15 })
            {
                using (var c = visual.RenderOpen()) player.Draw(c, "wave", "neutral", 0, 1 + elapsed, null, 1, true);
                var expected = new DrawingVisual();
                using (var c = expected.RenderOpen()) c.DrawImage(LuluVideo.Frame("wave", elapsed), new Rect(0, 0, 200, 200));
                if (!Render(visual).SequenceEqual(Render(expected)))
                    throw new Exception($"Transition at {elapsed:F3}s changes frame opacity or retains the old silhouette");
                var image = new RenderTargetBitmap(200, 200, 96, 96, PixelFormats.Pbgra32); image.Render(visual);
                strip.DrawRectangle(Brushes.DarkSlateGray, null, new Rect(column * 200, 0, 200, 200));
                strip.DrawImage(image, new Rect(column++ * 200, 0, 200, 200));
            }
        }
        var capture = new RenderTargetBitmap(1000, 200, 96, 96, PixelFormats.Pbgra32); capture.Render(sheet);
        var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(capture));
        using (var file = File.Create(Path.Combine(output, "transition-solid-frames.png"))) encoder.Save(file);
        // Repeated commands must restart; drag/fall must interrupt immediately.
        foreach (string key in new[] { "wave", "eat", "drag", "fall" })
        {
            using (var c = visual.RenderOpen()) player.Draw(c, key, "neutral", 0, 2, null, 2, true);
            var expected = new DrawingVisual();
            using (var c = expected.RenderOpen()) c.DrawImage(LuluVideo.Frame(key, 0), new Rect(0, 0, 200, 200));
            if (!Render(visual).SequenceEqual(Render(expected))) throw new Exception("Skipped action entrance: " + key);
        }
        log.Add("PASS switching frames match the original RGBA pixels at 0/25/60/100/150ms: no opacity dip, no old silhouette; replay and physical actions start immediately");
    }
}
