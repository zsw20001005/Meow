using System.IO;
using System.Reflection;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

internal static class EdgeChecks
{
    internal static int Run()
    {
        var output = Path.Combine(AppContext.BaseDirectory, "edge-checks"); Directory.CreateDirectory(output);
        var log = new List<string>();
        void Check(bool value, string message) { if (!value) throw new Exception(message); log.Add("PASS " + message); }
        static byte[] Pixels(BitmapSource f) { var a = new byte[f.PixelWidth * f.PixelHeight * 4]; f.CopyPixels(a, f.PixelWidth * 4, 0); return a; }
        static BitmapSource Render(string side, double time, double reveal)
        {
            var pet = new PetDrawing { Wall = side, Reveal = reveal, Time = time, Width = LuluEdgeAnimation.ViewWidth, Height = LuluEdgeAnimation.ViewHeight };
            pet.Measure(new Size(pet.Width, pet.Height)); pet.Arrange(new Rect(0, 0, pet.Width, pet.Height)); pet.UpdateLayout();
            var image = new RenderTargetBitmap((int)pet.Width, (int)pet.Height, 96, 96, PixelFormats.Pbgra32); image.Render(pet); image.Freeze(); return image;
        }
        static double Difference(BitmapSource a, BitmapSource b)
        {
            var aa = Pixels(a); var bb = Pixels(b); long sum = 0;
            for (int i = 0; i < aa.Length; i++) sum += Math.Abs(aa[i] - bb[i]);
            return (double)sum / aa.Length;
        }
        try
        {
            Check(LuluEdgeAnimation.Available && LuluEdgeAnimation.Count > 100, "dedicated edge loop available");
            Check(LuluEdgeAnimation.AnchorX > 0 && LuluEdgeAnimation.AnchorX < LuluEdgeAnimation.Frame(0).PixelWidth, "grip anchor lies inside the native frame");
            for (int i = 0; i < LuluEdgeAnimation.Count; i++)
            {
                var f = LuluEdgeAnimation.Frame(i / 24d); var pixels = Pixels(f);
                int opaque = 0, clear = 0;
                for (int p = 3; p < pixels.Length; p += 4) { if (pixels[p] > 240) opaque++; if (pixels[p] == 0) clear++; }
                Check(opaque > f.PixelWidth * f.PixelHeight * .2 && clear > f.PixelWidth * f.PixelHeight * .25, $"frame {i} character and transparent background");
            }
            var first = LuluEdgeAnimation.Frame(0);
            Check(ReferenceEquals(first, LuluEdgeAnimation.Frame(LuluEdgeAnimation.Duration * 100)), "100 loops reuse decoded frames and wrap exactly");
            double seam = Difference(first, LuluEdgeAnimation.Frame((LuluEdgeAnimation.Count - 1) / 24d));
            Check(seam < 2, $"registered final-to-first seam {seam:F3}/255");
            var right = Render("right", 2, 0); var left = Render("left", 2, 0); var rp = Pixels(right); var lp = Pixels(left);
            long mirrorError = 0;
            for (int y = 0; y < right.PixelHeight; y++) for (int x = 0; x < right.PixelWidth; x++) for (int c = 0; c < 4; c++)
                mirrorError += Math.Abs(rp[(y * right.PixelWidth + x) * 4 + c] - lp[(y * right.PixelWidth + right.PixelWidth - x - 1) * 4 + c]);
            Check((double)mirrorError / rp.Length < 1, "left/right rendering mirrors without rotating the head");
            Check(Difference(right, Render("right", 4, 0)) > .1, "real source breathing/blinking changes visible pixels");
            var temp = Path.Combine(Path.GetTempPath(), "meow-edge-" + Guid.NewGuid());
            var store = new Store(temp); store.Data.NightSleep = store.Data.Wander = store.Data.WindowJump = false;
            var window = new PetWindow(store); store.Data.WallSide = "right";
            var revealField = typeof(PetWindow).GetField("wallReveal", BindingFlags.NonPublic | BindingFlags.Instance)!;
            var step = typeof(PetWindow).GetMethod("FeatureFrame", BindingFlags.NonPublic | BindingFlags.Instance)!;
            revealField.SetValue(window, 0d); step.Invoke(window, new object[] { 0d, 0d }); var size = new Size(window.Width, window.Height);
            revealField.SetValue(window, 1d); step.Invoke(window, new object[] { 0d, 0d });
            Check(window.Width == size.Width && window.Height == size.Height, "hover preserves window width and height");
            var release = typeof(PetWindow).GetMethod("ReleaseWall", BindingFlags.NonPublic | BindingFlags.Instance)!; release.Invoke(window, null);
            Check(store.Data.WallSide == "" && window.Width == window.Height, "drag/action release restores normal pet bounds");
            window.Features.Stop(); window.Mailbox.Dispose(); window.Local.Dispose();
            var visual = new DrawingVisual();
            using (var dc = visual.RenderOpen())
            {
                dc.DrawRectangle(new SolidColorBrush(Color.FromRgb(23, 33, 49)), null, new Rect(0, 0, 792, 400));
                dc.DrawRectangle(Brushes.WhiteSmoke, null, new Rect(0, 200, 792, 200));
                for (int row = 0; row < 2; row++) for (int col = 0; col < 6; col++)
                {
                    string side = col % 2 == 0 ? "left" : "right"; double t = col < 2 ? 2 : col < 4 ? 4.5 : 8;
                    dc.DrawImage(Render(side, t, col >= 4 ? 1 : 0), new Rect(col * 132, row * 200 + 10, LuluEdgeAnimation.ViewWidth, LuluEdgeAnimation.ViewHeight));
                }
            }
            var sheet = new RenderTargetBitmap(792, 400, 96, 96, PixelFormats.Pbgra32); sheet.Render(visual);
            var encoder = new PngBitmapEncoder(); encoder.Frames.Add(BitmapFrame.Create(sheet)); using (var file = File.Create(Path.Combine(output, "edge-render.png"))) encoder.Save(file);
            log.Add("PASS actual WPF dark/light edge preview exported");
            File.WriteAllLines(Path.Combine(output, "results.txt"), log); return 0;
        }
        catch (Exception e) { log.Add("FAIL " + e); File.WriteAllLines(Path.Combine(output, "results.txt"), log); return 1; }
    }
}
