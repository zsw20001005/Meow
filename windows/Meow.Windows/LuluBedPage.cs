using System.IO;
using System.Text.Json;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Bed atlases can expand to 54 MiB each. Retain compressed independent frames
// instead; only the two static bed pictures need their own native bitmap.
internal sealed class LuluBedPage
{
    private readonly LuluFrameBuffer? frames;
    internal BitmapSource? Still { get; }
    private LuluBedPage(LuluFrameBuffer frames) { this.frames = frames; }
    private LuluBedPage(BitmapSource still) { Still = still; }
    internal void CopyFrame(int frame, byte[] pixels) => frames!.CopyFrame(frame, pixels);

    internal static LuluBedPage Load(string root, string name)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(root, "manifest.json")));
        var manifest = doc.RootElement;
        string prefix = manifest.TryGetProperty("assetPrefix", out var ap) ? ap.GetString()! : "";
        string path = Path.Combine(root, prefix + name + ".png");
        BitmapSource ReadImage()
        {
            using var stream = File.OpenRead(path);
            var decoder = BitmapDecoder.Create(stream, BitmapCreateOptions.PreservePixelFormat, BitmapCacheOption.OnLoad);
            return new FormatConvertedBitmap(decoder.Frames[0], PixelFormats.Pbgra32, null, 0);
        }
        if (name is "arrive-bed" or "leave-bed")
        {
            var image = ReadImage();
            var pixels = new byte[image.PixelWidth * image.PixelHeight * 4];
            image.CopyPixels(pixels, image.PixelWidth * 4, 0);
            var still = BitmapSource.Create(image.PixelWidth, image.PixelHeight, 96, 96, PixelFormats.Pbgra32, null, pixels, image.PixelWidth * 4);
            still.Freeze(); return new(still);
        }
        int separator = name.LastIndexOf('-');
        int page = int.Parse(name[(separator + 1)..], System.Globalization.CultureInfo.InvariantCulture);
        var clip = manifest.GetProperty("clips").GetProperty(name[..separator]);
        int scale = manifest.TryGetProperty("pixelScale", out var ps) ? ps.GetInt32() : 1;
        int width = (clip.TryGetProperty("width", out var cw) ? cw.GetInt32() : manifest.GetProperty("width").GetInt32()) * scale;
        int height = (clip.TryGetProperty("height", out var ch) ? ch.GetInt32() : manifest.GetProperty("height").GetInt32()) * scale;
        int pageFrames = manifest.GetProperty("pageFrames").GetInt32();
        int count = Math.Min(pageFrames, clip.GetProperty("frames").GetInt32() - page * pageFrames);
        return new(LuluFrameBuffer.Load(width, height, count, manifest.GetProperty("columns").GetInt32(), pageFrames, _ => ReadImage(),
            name.StartsWith("join-", StringComparison.Ordinal) || name is "approach-0" or "wake-0" ? [path] : null));
    }
}
