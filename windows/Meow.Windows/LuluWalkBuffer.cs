using System.IO;
using System.Text.Json;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Lossless departure frames prepared during arrival. Playback expands into
// the scene's reusable WriteableBitmap; the buffer dies with that scene.
internal sealed class LuluWalkBuffer
{
    private static readonly object preparationLock = new();
    private static WeakReference<Task<LuluWalkBuffer>>? preparation;
    private readonly LuluFrameBuffer frames;
    internal int Width => frames.Width;
    internal int Height => frames.Height;
    private LuluWalkBuffer(LuluFrameBuffer frames) { this.frames = frames; }

    internal static Task<LuluWalkBuffer> Prepare(string root)
    {
        lock (preparationLock)
        {
            // Overlapping scenes/previews share work without permanently rooting
            // the completed task and all of its frames after the last scene ends.
            if (preparation is not null && preparation.TryGetTarget(out var current) && !current.IsFaulted && !current.IsCanceled) return current;
            var task = Task.Run(() => Load(root));
            preparation = new(task); return task;
        }
    }

    internal static LuluWalkBuffer Load(string root)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "manifest.json")));
        var manifest = doc.RootElement; var clip = manifest.GetProperty("clips").GetProperty("depart");
        int width = clip.GetProperty("width").GetInt32(), height = clip.GetProperty("height").GetInt32();
        int pixelScale = manifest.TryGetProperty("pixelScale", out var ps) ? ps.GetInt32() : 1;
        width *= pixelScale; height *= pixelScale;
        string prefix = manifest.TryGetProperty("assetPrefix", out var ap) ? ap.GetString()! : "";
        int columns = manifest.GetProperty("columns").GetInt32(), pageFrames = manifest.GetProperty("pageFrames").GetInt32();
        int count = clip.GetProperty("frames").GetInt32();
        return new(LuluFrameBuffer.Load(width, height, count, columns, pageFrames, page =>
        {
            var decoder = BitmapDecoder.Create(new Uri(Path.Combine(root, $"{prefix}depart-{page}.png")), BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
            var image = new FormatConvertedBitmap(decoder.Frames[0], PixelFormats.Pbgra32, null, 0);
            var pixels = new byte[image.PixelWidth * image.PixelHeight * 4];
            int stride = image.PixelWidth * 4; image.CopyPixels(pixels, stride, 0);
            var decoded = BitmapSource.Create(image.PixelWidth, image.PixelHeight, 96, 96, PixelFormats.Pbgra32, null, pixels, stride);
            decoded.Freeze(); return decoded;
        }, Enumerable.Range(0, (count + pageFrames - 1) / pageFrames).Select(page => Path.Combine(root, $"{prefix}depart-{page}.png")).ToArray()));
    }

    internal void CopyFrame(int index, byte[] destination)
    {
        frames.CopyFrame(index, destination);
    }
}
