using System.Buffers.Binary;
using System.IO;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;

namespace Meow.Windows;

// WPF's text renderer does not paint COLR layers. Read the installed Windows
// emoji font's COLRv0/CPAL tables, then let WPF rasterize those vector layers.
// No font file is copied or shipped. Unsupported fonts fall back to ordinary text.
// Layout: https://learn.microsoft.com/typography/opentype/spec/colr (and /cpal).
internal static class ColorEmoji
{
    private static readonly Dictionary<string, Drawing?> Cache = [];
    private static readonly GlyphTypeface? Typeface;
    private static readonly byte[] FontBytes = [];
    private static readonly Dictionary<ushort, (int First, int Count)> Glyphs = [];
    private static readonly int Layers, Colors, PaletteStart;
    static ColorEmoji()
    {
        try
        {
            string font = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Fonts), "seguiemj.ttf");
            FontBytes = File.ReadAllBytes(font); Typeface = new GlyphTypeface(new Uri(font));
            int colr = 0, cpal = 0;
            for (int i = 0; i < U16(4); i++) { int record = 12 + i * 16; string tag = Encoding.ASCII.GetString(FontBytes, record, 4); if (tag == "COLR") colr = U32(record + 8); if (tag == "CPAL") cpal = U32(record + 8); }
            if (colr == 0 || cpal == 0) return;
            int bases = colr + U32(colr + 4); Layers = colr + U32(colr + 8); Colors = cpal + U32(cpal + 8); PaletteStart = U16(cpal + 12);
            for (int i = 0; i < U16(colr + 2); i++) { int record = bases + i * 6; Glyphs[U16(record)] = (U16(record + 2), U16(record + 4)); }
        }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException or ArgumentException or NotSupportedException or OverflowException) { Glyphs.Clear(); }
    }
    private static ushort U16(int offset) => BinaryPrimitives.ReadUInt16BigEndian(FontBytes.AsSpan(offset, 2));
    private static int U32(int offset) => checked((int)BinaryPrimitives.ReadUInt32BigEndian(FontBytes.AsSpan(offset, 4)));
    internal static Drawing? Get(string emoji)
    {
        if (Cache.TryGetValue(emoji, out var cached)) return cached;
        if (Typeface is null || !Typeface.CharacterToGlyphMap.TryGetValue(char.ConvertToUtf32(emoji, 0), out var glyph) || !Glyphs.TryGetValue(glyph, out var layers)) return Cache[emoji] = null;
        var drawing = new DrawingGroup();
        for (int i = 0; i < layers.Count; i++)
        {
            int record = Layers + (layers.First + i) * 4, palette = U16(record + 2); Brush brush = MacTheme.Cocoa;
            if (palette != ushort.MaxValue) { int color = Colors + (PaletteStart + palette) * 4; brush = new SolidColorBrush(Color.FromArgb(FontBytes[color + 3], FontBytes[color + 2], FontBytes[color + 1], FontBytes[color])); }
            drawing.Children.Add(new GeometryDrawing(brush, null, Typeface.GetGlyphOutline(U16(record), 100, 100)));
        }
        drawing.Freeze(); return Cache[emoji] = drawing;
    }
    internal static FrameworkElement Icon(string emoji, double size)
    {
        if (Get(emoji) is { } drawing) return new Image { Source = new DrawingImage(drawing), Width = size, Height = size, Stretch = Stretch.Uniform };
        return MacTheme.Text(emoji, size);
    }
    internal static bool Draw(DrawingContext context, string emoji, double x, double y, double size)
    {
        if (Get(emoji) is not { } drawing) return false;
        Rect bounds = drawing.Bounds; double scale = size / Math.Max(bounds.Width, bounds.Height);
        context.PushTransform(new TranslateTransform(x - bounds.Width * scale / 2, y - bounds.Height * scale / 2)); context.PushTransform(new ScaleTransform(scale, scale)); context.PushTransform(new TranslateTransform(-bounds.X, -bounds.Y)); context.DrawDrawing(drawing); context.Pop(); context.Pop(); context.Pop(); return true;
    }
}
