using System.IO;

namespace Meow.Windows;

internal static class DiskFrameChecks
{
    internal static int Run()
    {
        var log = new List<string>(); var caches = new HashSet<string>();
        string source = Path.Combine(Path.GetTempPath(), "meow-packet-check-" + Guid.NewGuid() + ".source");
        void Check(bool value, string message) { if (!value) throw new Exception(message); log.Add("PASS " + message); }
        var payload = Enumerable.Range(0, 20).Select(i => new byte[] { (byte)i, 42, 255 }).ToArray();
        try
        {
            File.WriteAllText(source, "first"); int encodes = 0;
            IEnumerable<byte[]> Encode() { encodes++; return payload; }
            var disk = LuluDiskFrames.OpenOrBuild([source], 16, 16, payload.Length, Encode); caches.Add(disk.FilePath);
            for (int i = 0; i < 200; i++)
            {
                int index = i * 7 % payload.Length;
                Check(disk.Get(index).AsSpan().SequenceEqual(payload[index]), $"packet seek {i} returns exact bytes");
            }
            Check(disk.CachedPacketCount <= 8, "random seeks keep compressed packet cache bounded");
            var reused = LuluDiskFrames.OpenOrBuild([source], 16, 16, payload.Length, () => throw new Exception("Cache unexpectedly re-encoded"));
            Check(reused.Get(19).AsSpan().SequenceEqual(payload[19]) && encodes == 1, "next load uses indexed disk data without source decoding");
            File.WriteAllBytes(disk.FilePath, new byte[16]);
            var repaired = LuluDiskFrames.OpenOrBuild([source], 16, 16, payload.Length, Encode);
            Check(encodes == 2 && repaired.Get(0).AsSpan().SequenceEqual(payload[0]), "corrupt header regenerates derived cache");
            File.AppendAllText(source, "changed");
            var changed = LuluDiskFrames.OpenOrBuild([source], 16, 16, payload.Length, Encode); caches.Add(changed.FilePath);
            Check(encodes == 3 && changed.FilePath != disk.FilePath, "source update invalidates the old packet cache");
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "disk-frame-checks.txt"), log); return 0;
        }
        catch (Exception error) { log.Add("FAIL " + error); File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "disk-frame-checks.txt"), log); return 1; }
        finally { foreach (string cache in caches) if (File.Exists(cache)) File.Delete(cache); if (File.Exists(source)) File.Delete(source); }
    }
}
