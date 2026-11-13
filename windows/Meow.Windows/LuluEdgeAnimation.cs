using System.IO;
using System.Text.Json;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// A dedicated upright edge loop backed by a bounded packet cache.
internal static class LuluEdgeAnimation
{
    private static readonly string Root = Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", "Edge");
    private sealed record Layout(int Width, int Height, int Columns, int PageFrames, int Frames, double Fps, double AnchorX);
    private static readonly Layout? Info = ReadLayout();
    private static readonly Lazy<Task<LuluFrameBuffer>> Frames = new(() => Task.Run(Decode));
    internal static bool Available => Info is not null;
    internal static double Duration => Info is null ? 0 : Info.Frames / Info.Fps;
    internal static int Count => Info?.Frames ?? 0;
    internal static double AnchorX => Info?.AnchorX ?? 0;
    internal const double ViewWidth = 108;
    internal const double ViewHeight = 150;
    internal static void WarmUp() { if (Available) _ = Frames.Value; }
    private static Layout? ReadLayout()
    {
        var path = Path.Combine(Root, "manifest.json");
        if (!File.Exists(path)) return null;
        using var doc = JsonDocument.Parse(File.ReadAllText(path)); var m = doc.RootElement;
        return new(m.GetProperty("width").GetInt32(), m.GetProperty("height").GetInt32(),
            m.GetProperty("columns").GetInt32(), m.GetProperty("pageFrames").GetInt32(),
            m.GetProperty("frames").GetInt32(), m.GetProperty("fps").GetDouble(), m.GetProperty("anchorX").GetDouble());
    }
    private static LuluFrameBuffer Decode()
    {
        var m = Info!;
        return LuluFrameBuffer.Load(m.Width, m.Height, m.Frames, m.Columns, m.PageFrames, page =>
        {
            var bitmap = new BitmapImage(); bitmap.BeginInit(); bitmap.CacheOption = BitmapCacheOption.OnLoad;
            bitmap.UriSource = new Uri(Path.Combine(Root, $"edge-{page}.png")); bitmap.EndInit(); bitmap.Freeze();
            return new FormatConvertedBitmap(bitmap, PixelFormats.Pbgra32, null, 0);
        }, Enumerable.Range(0, (m.Frames + m.PageFrames - 1) / m.PageFrames).Select(page => Path.Combine(Root, $"edge-{page}.png")).ToArray());
    }
    internal static BitmapSource Frame(double seconds)
    {
        var m = Info!;
        int index = (int)(Math.Max(0, seconds) * m.Fps + 1e-7) % m.Frames;
        return Frames.Value.GetAwaiter().GetResult().Frame(index);
    }
    internal static void Draw(DrawingContext dc, string side, double time, double reveal, double width, double height, LuluPlaybackFrame playback)
    {
        var m = Info!; int index = (int)(Math.Max(0, time) * m.Fps + 1e-7) % m.Frames;
        var frame = playback.Update(m, index, m.Width, m.Height, pixels => Frames.Value.GetAwaiter().GetResult().CopyFrame(index, pixels));
        double k = height / ViewHeight;
        // Uniform scale around the grip, never stretching width independently.
        double scale = (height - 8 * k) / m.Height * (1 + .035 * Math.Clamp(reveal, 0, 1));
        double enter = Math.Clamp(time / .32, 0, 1); enter = enter * enter * (3 - 2 * enter);
        double x = width - m.AnchorX * scale + 12 * k * (1 - enter);
        double y = 4 * k - ViewHeight * .60 * k * .035 * Math.Clamp(reveal, 0, 1);
        dc.PushClip(new RectangleGeometry(new Rect(0, 0, width, height)));
        if (side == "left") dc.PushTransform(new ScaleTransform(-1, 1, width / 2, 0));
        dc.DrawImage(frame, new Rect(x, y, m.Width * scale, m.Height * scale));
        if (side == "left") dc.Pop();
        dc.Pop();
    }
}
