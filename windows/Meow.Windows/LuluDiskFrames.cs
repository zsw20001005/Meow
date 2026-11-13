using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace Meow.Windows;

// Indexed, lossless frame packets. The OS may cache file pages, but the pet only
// retains eight small compressed packets, not a complete long animation.
internal sealed class LuluDiskFrames
{
    private const int Magic = 0x31464C4D;
    private readonly string path;
    private readonly (long Offset, int Length)[] entries;
    private readonly Dictionary<int, byte[]> packets = new();
    private readonly LinkedList<int> recent = new();
    private bool prefetching;
    internal int Width { get; }
    internal int Height { get; }
    internal long Bytes { get; }
    internal string FilePath => path;
    internal int CachedPacketCount { get { lock (packets) return packets.Count; } }
    private LuluDiskFrames(string path, int width, int height, (long, int)[] entries, long bytes)
    { this.path = path; Width = width; Height = height; this.entries = entries; Bytes = bytes; }

    internal static LuluDiskFrames OpenOrBuild(string[] sources, int width, int height, int count, Func<IEnumerable<byte[]>> encode)
    {
        string stamp = $"v1:{width}:{height}:{count}:" + string.Join("|", sources.Select(file =>
        { var info = new FileInfo(file); return $"{info.Name}:{info.Length}:{info.LastWriteTimeUtc.Ticks}"; }));
        string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Meow.Windows", "AnimationCache");
        Directory.CreateDirectory(root);
        string path = Path.Combine(root, Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(stamp))) + ".lframes");
        try { return Read(path, width, height, count); }
        catch (Exception error) when (error is IOException or InvalidDataException) { }
        string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            using (var output = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
            using (var writer = new BinaryWriter(output))
            {
                writer.Write(Magic); writer.Write(width); writer.Write(height); writer.Write(count);
                var entries = new (long Offset, int Length)[count];
                output.Position = 16L + count * 12L; int index = 0;
                foreach (var bytes in encode())
                {
                    if (index >= count) throw new InvalidDataException("Too many packed frames.");
                    entries[index++] = (output.Position, bytes.Length); writer.Write(bytes);
                }
                if (index != count) throw new InvalidDataException("Incomplete frame packet cache.");
                output.Position = 16;
                foreach (var entry in entries) { writer.Write(entry.Offset); writer.Write(entry.Length); }
            }
            File.Move(temporary, path, overwrite: true);
            return Read(path, width, height, count);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    private static LuluDiskFrames Read(string path, int width, int height, int count)
    {
        using var input = File.OpenRead(path); using var reader = new BinaryReader(input);
        if (reader.ReadInt32() != Magic || reader.ReadInt32() != width || reader.ReadInt32() != height || reader.ReadInt32() != count)
            throw new InvalidDataException("Unexpected frame packet layout.");
        var entries = new (long Offset, int Length)[count]; long expected = 16L + count * 12L;
        for (int i = 0; i < count; i++)
        {
            long offset = reader.ReadInt64(); int length = reader.ReadInt32();
            if (offset != expected || length <= 0 || length > (long)width * height * 4 + 16384 || offset + length > input.Length)
                throw new InvalidDataException("Invalid frame packet index.");
            entries[i] = (offset, length); expected += length;
        }
        if (expected != input.Length) throw new InvalidDataException("Unexpected frame packet data length.");
        return new(path, width, height, entries, input.Length);
    }

    private byte[] ReadPacket(int index)
    {
        lock (packets)
        {
            if (!packets.TryGetValue(index, out var bytes))
            {
                var entry = entries[index]; bytes = new byte[entry.Length];
                using var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read | FileShare.Delete);
                input.Position = entry.Offset; input.ReadExactly(bytes); packets[index] = bytes;
            }
            recent.Remove(index); recent.AddLast(index);
            while (recent.Count > 8) { packets.Remove(recent.First!.Value); recent.RemoveFirst(); }
            return bytes;
        }
    }

    internal byte[] Get(int index)
    {
        var bytes = ReadPacket(index);
        lock (packets)
        {
            if (!prefetching)
            {
                prefetching = true;
                _ = Task.Run(() =>
                {
                    try { for (int i = 1; i <= 4; i++) ReadPacket((index + i) % entries.Length); }
                    catch (Exception error) when (error is IOException or UnauthorizedAccessException) { /* Foreground read reports an actual missing packet. */ }
                    finally { lock (packets) prefetching = false; }
                });
            }
        }
        return bytes;
    }
}
