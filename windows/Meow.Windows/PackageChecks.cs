using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class PackageChecks
{
    internal static int Run(bool coreOnly)
    {
        var results = new List<string>();
        void Check(bool ok, string name) { if (!ok) throw new InvalidDataException(name); results.Add("PASS " + name); }
        try
        {
            foreach (string clip in new[] { "idle", "walk", "talk", "wave", "happy", "think", "sleep", "drag", "fall", "land", "jump" })
                Check(LuluVideo.Clips.ContainsKey(clip), "base clip " + clip);
            Check(LuluEdgeAnimation.Available, "dedicated edge animation included");
            Check(coreOnly ? LuluVideo.MissingClips.Count > 0 : LuluVideo.MissingClips.Count == 0, "expected optional clip availability");
            Check(!PetWindow.RequiresMotionPack(new("", "happy", ["wave"])), "base behavior needs no extension");
            Check(PetWindow.RequiresMotionPack(new("", "neutral", ["wave", "eat"])) == coreOnly, "queued missing action reports unavailable before starting");
            Check(PetWindow.RequiresMotionPack(new("", "angry", [])) == coreOnly, "missing expression reports unavailable");
            Check(LuluBedScene.Available != coreOnly, "expected bed availability");
            Check(File.Exists(Path.Combine(AppContext.BaseDirectory, "mailbridge", "node.exe")) != coreOnly, "expected mail availability");
            foreach (var (key, clip) in LuluVideo.Clips)
            {
                Check(LuluVideo.Frame(key, 0).PixelWidth == LuluVideo.CellSize, key + " first frame");
                Check(LuluVideo.Frame(key, (clip.Frames - 1) / clip.Fps).PixelWidth == LuluVideo.CellSize, key + " last frame");
            }
            var drawing = new PetDrawing { Width = 200, Height = 200 };
            drawing.Measure(new Size(200, 200)); drawing.Arrange(new Rect(0, 0, 200, 200));
            foreach (var action in new[] { "idle", "wave", "walk", "sleep", "eat", "play", "spin" })
            {
                drawing.Action = action; drawing.Time += .25; drawing.InvalidateVisual(); drawing.UpdateLayout();
                var bitmap = new RenderTargetBitmap(200, 200, 96, 96, PixelFormats.Pbgra32); bitmap.Render(drawing);
                Check(bitmap.PixelWidth == 200, "render with optional packs present/absent: " + action);
            }
            if (coreOnly)
            {
                using var mail = new MailboxService(new Store(Path.Combine(Path.GetTempPath(), "meow-package-" + Guid.NewGuid())));
                try { mail.Start().GetAwaiter().GetResult(); throw new Exception("Missing mail pack did not fail"); }
                catch (IOException e) { Check(e.Message.Contains("信箱扩展包"), "missing mail pack has actionable message"); }
            }
            results.Add("All package checks passed.");
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "package-checks.txt"), results); return 0;
        }
        catch (Exception error)
        {
            results.Add("FAIL " + error); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "package-checks.txt"), results); return 1;
        }
    }
}
