using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class StrollChecks
{
    internal static int Run()
    {
        string output = Path.Combine(AppContext.BaseDirectory, "stroll-checks"); Directory.CreateDirectory(output);
        string temp = Path.Combine(Path.GetTempPath(), "meow-stroll-" + Guid.NewGuid());
        var log = new List<string>(); PetWindow? window = null;
        FieldInfo Field(string name) => typeof(PetWindow).GetField(name, BindingFlags.NonPublic | BindingFlags.Instance)!;
        void Check(bool valid, string name) { if (!valid) throw new Exception(name); log.Add("PASS " + name); }
        static BitmapSource Render(PetDrawing pet)
        {
            pet.Width = pet.Height = 256; pet.Measure(new Size(256, 256)); pet.Arrange(new Rect(0, 0, 256, 256)); pet.InvalidateVisual(); pet.UpdateLayout();
            var image = new RenderTargetBitmap(256, 256, 96, 96, PixelFormats.Pbgra32); image.Render(pet); image.Freeze(); return image;
        }
        static byte[] Pixels(BitmapSource image)
        {
            if (image.PixelWidth != 256 || image.PixelHeight != 256)
            {
                var display = new System.Windows.Controls.Image { Width = 256, Height = 256, Source = image };
                RenderOptions.SetBitmapScalingMode(display, BitmapScalingMode.HighQuality);
                display.Measure(new Size(256, 256)); display.Arrange(new Rect(0, 0, 256, 256));
                var target = new RenderTargetBitmap(256, 256, 96, 96, PixelFormats.Pbgra32); target.Render(display); image = target;
            }
            var bytes = new byte[256 * 256 * 4]; image.CopyPixels(bytes, 1024, 0); return bytes;
        }
        static void Save(BitmapSource image, string path)
        { var png = new PngBitmapEncoder(); png.Frames.Add(BitmapFrame.Create(image)); using var stream = File.Create(path); png.Save(stream); }
        static bool SameEndpoint(BitmapSource actual, BitmapSource captured)
        {
            var a = Pixels(actual); var b = Pixels(captured);
            // A RenderTargetBitmap capture can round premultiplied colour by
            // one code value. Geometry/alpha must still match exactly.
            for (int i = 0; i < a.Length; i++)
                if (Math.Abs(a[i] - b[i]) > (i % 4 == 3 ? 0 : 1)) return false;
            return true;
        }
        try
        {
            var store = new Store(temp); store.Data.Scale = 256d / 230;
            store.Data.MemoryEnabled = store.Data.Wander = store.Data.NightSleep = store.Data.WindowJump = false;
            window = new PetWindow(store); var pet = (PetDrawing)Field("pet").GetValue(window)!;
            var area = (Rect)typeof(PetWindow).GetProperty("Area", BindingFlags.NonPublic | BindingFlags.Instance)!.GetValue(window)!;
            double origin = area.Left + 32; window.Left = origin;
            var before = Render(pet); window.Animate("walk");
            var startPose = Render(pet);
            Save(before, Path.Combine(output, "start-before.png")); Save(startPose, Path.Combine(output, "start-after.png"));
            Check(Pixels(before).SequenceEqual(Pixels(startPose)), "start preserves the actually displayed idle pose");
            int starts = 0, rests = 0, joins = 0; string lastPhase = "";
            double restPosition = 0; byte[]? restFirst = null; bool idleMoved = false;
            string frames = Path.Combine(output, "frames"); Directory.CreateDirectory(frames);
            for (int i = 0; i < 1200; i++)
            {
                pet.Time = i / 60d;
                var transition = pet.PoseTransition;
                transition?.Preparation.GetAwaiter().GetResult();
                if (i > 0) window.AdvanceStroll(1d / 60);
                var image = Render(pet);
                if (transition is not null && pet.PoseTransition is null)
                {
                    Save(image, Path.Combine(output, "endpoint-actual.png")); Save(transition.Preparation.Result[^1], Path.Combine(output, "endpoint-source.png"));
                    Check(SameEndpoint(image, transition.Preparation.Result[^1]), "transition endpoint keeps exact alpha and colour within 1/255 capture rounding"); joins++;
                }
                string phase = (string)Field("strollPhase").GetValue(window)!;
                if (phase != lastPhase)
                {
                    log.Add($"phase {phase} at {i / 60d:F3}s, x={window.Left:F2}");
                    if (phase == "walking") starts++;
                    if (phase == "resting") { rests++; restPosition = window.Left; restFirst = Pixels(image); }
                    Save(image, Path.Combine(output, $"phase-{i:D4}-{phase}.png"));
                    lastPhase = phase;
                }
                if (phase == "resting")
                {
                    if (Math.Abs(window.Left - restPosition) > .001) throw new Exception("Pet slides while resting");
                    idleMoved |= !Pixels(image).SequenceEqual(restFirst!);
                    if ((string)Field("heldState").GetValue(window)! != "walk") throw new Exception("Rest loses the stroll mode");
                }
                if (transition is not null && i % 5 == 0) Save(image, Path.Combine(output, $"join-{i:D4}.png"));
                var stage = new DrawingVisual(); using (var dc = stage.RenderOpen())
                {
                    dc.DrawRectangle(Brushes.DarkSlateGray, null, new Rect(0, 0, 768, 256));
                    dc.DrawImage(image, new Rect(window.Left - origin + 40, 0, 256, 256));
                }
                var capture = new RenderTargetBitmap(768, 256, 96, 96, PixelFormats.Pbgra32); capture.Render(stage);
                Save(capture, Path.Combine(frames, $"{i:D4}.png"));
            }
            Check(starts >= 2 && rests >= 2 && joins >= 4, "20 seconds includes repeated walking and resting with both joins");
            Check(idleMoved, "rest retains living idle animation rather than a frozen pose");
            window.Animate("idle");
            for (int i = 0; i < 600; i++)
            {
                var pending = pet.PoseTransition; pending?.Preparation.GetAwaiter().GetResult(); window.AdvanceStroll(1d / 60);
                var image = Render(pet);
                if (pending is not null && pet.PoseTransition is null)
                    Check(SameEndpoint(image, pending.Preparation.Result[^1]), "manual stop keeps idle endpoint alpha and bounded capture rounding");
            }
            Check(pet.Action == "idle" && (string)Field("strollPhase").GetValue(window)! == "", "manual stop does not restart walking later");
            window.Animate("walk"); window.Animate("wave");
            Check(pet.PoseTransition is null && pet.PosePhase is null && (string)Field("strollPhase").GetValue(window)! == "" && pet.Action == "wave", "new action clears stroll transitions and pose override");
            window.Animate("walk"); window.Animate("sleep");
            Check((string)Field("strollPhase").GetValue(window)! == "" && pet.BedScene is not null, "sleep replaces stroll without sharing its timer");
            File.WriteAllText(Path.Combine(frames, "frame-count.txt"), "1200"); File.WriteAllText(Path.Combine(frames, "frame-rate.txt"), "60");
            return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); return 1; }
        finally
        {
            if (window is not null) { Field("closing").SetValue(window, true); window.Close(); }
            if (Directory.Exists(temp)) Directory.Delete(temp, true);
            File.WriteAllLines(Path.Combine(output, "results.txt"), log);
        }
    }
}
