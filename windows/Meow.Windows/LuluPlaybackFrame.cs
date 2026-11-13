using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace Meow.Windows;

// One renderer-owned surface. Repainting a 24 fps source at desktop refresh
// rate must not create new WIC bitmaps (or retain entire source atlases).
internal sealed class LuluPlaybackFrame
{
    private WriteableBitmap? image;
    private byte[] pixels = [];
    private object? source;
    private int index = -1;

    internal BitmapSource Update(object source, int index, int width, int height, Action<byte[]> copy)
    {
        if (image is not null && ReferenceEquals(this.source, source) && this.index == index) return image;
        if (image is null || image.PixelWidth != width || image.PixelHeight != height)
        {
            image = new WriteableBitmap(width, height, 96, 96, PixelFormats.Pbgra32, null);
            pixels = new byte[width * height * 4];
        }
        copy(pixels);
        image.WritePixels(new Int32Rect(0, 0, width, height), pixels, width * 4, 0);
        this.source = source; this.index = index;
        return image;
    }
}
