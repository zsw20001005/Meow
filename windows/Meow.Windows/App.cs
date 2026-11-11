using System.Windows;

namespace Meow.Windows;

public sealed class App : Application
{
    private Mutex? instance;
    [STAThread]
    public static int Main(string[] args)
    {
        if (args.Contains("--selftest")) return SelfTests.Run();
        if (args.Contains("--mailcheck")) return IntegrationChecks.Mail().GetAwaiter().GetResult();
        if (args.Contains("--cloudcheck")) return IntegrationChecks.Cloud().GetAwaiter().GetResult();
        if (args.Contains("--featurecheck")) return IntegrationChecks.Features().GetAwaiter().GetResult();
        if (args.Contains("--localcheck")) return IntegrationChecks.Local().GetAwaiter().GetResult();
        if (args.Contains("--rendercheck")) { _ = new App(); return VisualChecks.Run(); }
        if (args.Contains("--animationcheck")) { _ = new App(); return AnimationChecks.Run(); }
        if (args.Contains("--edgecheck")) { _ = new App(); return EdgeChecks.Run(); }
        if (args.Contains("--conversationcheck")) { _ = new App(); return ConversationChecks.RunRuntime(); }
        if (args.Contains("--bedcheck")) { _ = new App(); return BedSceneChecks.Run(); }
        if (args.Contains("--bed-entrycheck")) { _ = new App(); return BedEntryChecks.Run(); }
        if (args.Contains("--strollcheck")) { _ = new App(); return StrollChecks.Run(); }
        if (args.Contains("--bed-seamframes")) { _ = new App(); return BedSceneChecks.ExportSeams(); }
        if (args.Contains("--bed-film")) { _ = new App(); return BedSceneChecks.RenderFilm(); }
        if (args.Contains("--bed-walk-film")) { _ = new App(); return BedSceneChecks.RenderFilm(walkOnly: true); }
        if (args.Contains("--bed-profile")) { _ = new App(); return BedRenderProfile.Run(); }
        var app = new App { ShutdownMode = ShutdownMode.OnExplicitShutdown };
        if (args.Contains("--bed-preview")) { app.ShutdownMode = ShutdownMode.OnMainWindowClose; app.Run(new BedPreview()); return 0; }
        if (args.Contains("--bed-walk-preview")) { app.ShutdownMode = ShutdownMode.OnMainWindowClose; app.Run(new BedPreview(walkOnly: true)); return 0; }
        if (args.Contains("--character-preview")) { app.ShutdownMode = ShutdownMode.OnMainWindowClose; app.Run(new CharacterPreview()); return 0; }
        if (args.Contains("--visual-preview")) { app.Run(new PetWindow(VisualChecks.Sample())); return 0; }
        app.instance = new Mutex(true, @"Local\Meow.Windows", out bool first);
        if (!first) { if (EventWaitHandle.TryOpenExisting(@"Local\Meow.Windows.Show", out var signal)) { signal.Set(); signal.Dispose(); } else MessageBox.Show("噜噜已经在桌面上啦。", "Meow"); app.instance.Dispose(); return 0; }
        try
        {
            var store = new Store();
            var pet = new PetWindow(store);
            using var openEvent = new EventWaitHandle(false, EventResetMode.AutoReset, @"Local\Meow.Windows.Show");
            var listener = ThreadPool.RegisterWaitForSingleObject(openEvent, (_, _) => app.Dispatcher.BeginInvoke(pet.OpenDashboard), null, Timeout.Infinite, false);
            if (args.Contains("--open")) pet.Loaded += (_, _) => pet.OpenDashboard();
            try { app.Run(pet); } finally { listener.Unregister(null); }
            return 0;
        }
        catch (Exception e) { MessageBox.Show("噜噜启动失败：" + e.Message, "Meow"); return 1; }
        finally { app.instance.ReleaseMutex(); app.instance.Dispose(); }
    }
}
