using System.IO;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// Fixed raster parts, never a sequence of independently generated whole bodies.
// Each part keeps its proportions while joint transforms animate continuously.
internal sealed class LuluRigAssets
{
    internal static readonly LuluRigAssets Parts = new("rig-parts.png", 4, 2);
    internal static readonly LuluRigAssets Faces = new("rig-faces.png", 4, 2);
    internal static readonly LuluRigAssets Extra = new("rig-extra.png", 2, 2);
    internal static IEnumerable<LuluRigAssets> All => [Parts, Faces, Extra];
    private readonly BitmapSource[] parts;
    internal string FileName { get; }
    internal int PixelWidth { get; }
    internal int PixelHeight { get; }
    internal int Count => parts.Length;

    private LuluRigAssets(string file, int columns, int rows)
    {
        FileName = file;
        var image = new BitmapImage(); image.BeginInit(); image.CacheOption = BitmapCacheOption.OnLoad;
        image.UriSource = new Uri(Path.Combine(AppContext.BaseDirectory, "Assets", "Lulu", file)); image.EndInit(); image.Freeze();
        PixelWidth = image.PixelWidth; PixelHeight = image.PixelHeight; parts = new BitmapSource[columns * rows];
        for (int row = 0; row < rows; row++) for (int col = 0; col < columns; col++)
        {
            int x = col * image.PixelWidth / columns, y = row * image.PixelHeight / rows;
            int w = (col + 1) * image.PixelWidth / columns - x, h = (row + 1) * image.PixelHeight / rows - y;
            var cell = new CroppedBitmap(image, new Int32Rect(x, y, w, h));
            var rgba = new FormatConvertedBitmap(cell, PixelFormats.Bgra32, null, 0);
            var pixels = new byte[w * h * 4]; rgba.CopyPixels(pixels, w * 4, 0);
            int left = w, top = h, right = -1, bottom = -1, clear = 0;
            for (int cy = 0; cy < h; cy++) for (int cx = 0; cx < w; cx++)
            {
                byte alpha = pixels[(cy * w + cx) * 4 + 3]; if (alpha < 8) clear++;
                if (alpha < 96) continue;
                left = Math.Min(left, cx); right = Math.Max(right, cx); top = Math.Min(top, cy); bottom = Math.Max(bottom, cy);
            }
            if (right < left || clear < w * h / 10) throw new InvalidDataException($"Invalid transparent Lulu part: {file}, {row * columns + col}");
            left = Math.Max(0, left - 3); top = Math.Max(0, top - 3); right = Math.Min(w - 1, right + 3); bottom = Math.Min(h - 1, bottom + 3);
            var part = new CroppedBitmap(cell, new Int32Rect(left, top, right - left + 1, bottom - top + 1)); part.Freeze(); parts[row * columns + col] = part;
        }
    }

    internal void Draw(DrawingContext context, int index, Rect target)
    {
        var part = parts[index]; double scale = Math.Min(target.Width / part.PixelWidth, target.Height / part.PixelHeight);
        double w = part.PixelWidth * scale, h = part.PixelHeight * scale;
        context.DrawImage(part, new Rect(target.X + (target.Width - w) / 2, target.Y + (target.Height - h) / 2, w, h));
    }
}
