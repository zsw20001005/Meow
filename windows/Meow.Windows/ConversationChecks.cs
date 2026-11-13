using System.IO;
using System.Text;
using System.Text.Json;
using System.Reflection;

namespace Meow.Windows;

internal static class ConversationChecks
{
    internal static int RunRuntime()
    {
        string directory = Path.Combine(Path.GetTempPath(), "meow-conversation-" + Guid.NewGuid());
        var log = new List<string>(); PetWindow? window = null;
        void Check(bool valid, string name) { if (!valid) throw new Exception(name); log.Add("PASS " + name); }
        FieldInfo Field(string name) => typeof(PetWindow).GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)!;
        void Set(string name, object value) => Field(name).SetValue(window, value);
        void AdvanceBed(double seconds)
        {
            var pet = (PetDrawing)Field("pet").GetValue(window)!;
            for (double remaining = seconds; remaining > 1e-9; remaining -= 1d / 60)
            {
                pet.PoseTransition?.Preparation.GetAwaiter().GetResult();
                window!.AdvanceBedScene(Math.Min(1d / 60, remaining));
            }
        }
        void Expire()
        {
            Set("actionUntil", -1d);
            typeof(PetWindow).GetMethod("Tick", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, [null, EventArgs.Empty]);
        }
        void AdvanceWalking(double seconds)
        {
            var pet = (PetDrawing)Field("pet").GetValue(window)!;
            for (double remaining = seconds; remaining > 1e-9; remaining -= 1d / 60)
            {
                pet.PoseTransition?.Preparation.GetAwaiter().GetResult();
                window!.AdvanceStroll(Math.Min(1d / 60, remaining));
            }
        }
        try
        {
            var store = new Store(directory);
            store.Data.MemoryEnabled = store.Data.Wander = store.Data.NightSleep = store.Data.WindowJump = false;
            store.Data.Fullness = 20;
            window = new PetWindow(store); Set("saveAt", double.MaxValue); Set("nextDecision", double.MaxValue);
            var drawing = (PetDrawing)Field("pet").GetValue(window)!;
            var playback = (ConversationPlayback)Field("conversationPlayback").GetValue(window)!;
            var reply = ConversationBehavior.Parse("{\"text\":\"谢谢主人\",\"emotion\":\"happy\",\"actions\":[\"eat\",\"wave\"],\"intent\":\"request\"}", "给你西瓜，再挥挥手");
            int revision = window.ConversationRevision;
            window.ReactToConversation(reply, revision);
            Check(drawing.Action == "eat" && store.Data.Fullness == 40, "real PetWindow starts eating and increments fullness once");
            window.ReactToConversation(reply, revision);
            Check(store.Data.Fullness == 40, "duplicate delivery cannot feed twice");
            Expire(); Check(drawing.Action == "wave", "render tick advances eating to waving");
            Expire(); Check(drawing.Action == "idle" && drawing.Emotion == "happy", "render tick advances action to expression without overlay");
            Expire(); Check(drawing.Action == "idle" && drawing.Emotion == "neutral" && !playback.Playing, "completed conversation returns to neutral idle");
            window.ReactToConversation(ActionLanguage.LocalPlan("先挥手，再转圈，最后点头")!, window.ConversationRevision);
            Check(drawing.Action == "wave", "local multi-action request starts first action");
            Expire(); Check(drawing.Action == "spin", "local multi-action request advances to second action");
            Expire(); Check(drawing.Action == "nod", "local multi-action request advances to third action");
            Expire(); Check(!playback.Playing, "three-step action queue finishes once");
            revision = window.ConversationRevision;
            window.ReactToConversation(reply, revision); window.Animate("idle");
            Check(!playback.Playing && drawing.Action == "idle", "manual stop clears running conversation");
            double fullness = store.Data.Fullness; window.ReactToConversation(reply, revision);
            Check(store.Data.Fullness == fullness && drawing.Action == "idle", "old reply cannot resume after manual stop");
            Set("dragging", true); window.ReactToConversation(reply, window.ConversationRevision);
            Check(!playback.Playing && store.Data.Fullness == fullness, "dragging blocks model behavior"); Set("dragging", false);
            Set("falling", true); window.ReactToConversation(reply, window.ConversationRevision);
            Check(!playback.Playing && store.Data.Fullness == fullness, "falling blocks model behavior"); Set("falling", false);
            window.ReactToConversation(new("晚安", "neutral", ["sleep"], Requested: true), window.ConversationRevision);
            Expire(); Check(drawing.Action == "sleep" && !playback.Playing, "sleep holds instead of being reset by conversation completion");
            window.Animate("idle");
            if (drawing.BedScene is not null)
            {
                Check(drawing.BedScene.WakeRequested && drawing.Action == "sleep", "wake request waits for the bed exit animation");
                AdvanceBed(40);
            }
            Check(drawing.Action == "idle" && drawing.BedScene is null, "wake completes before returning to idle");
            window.Animate("sleep"); if (drawing.BedScene is not null || drawing.BedApproaching) AdvanceBed(20);
            window.ReactToConversation(ActionLanguage.LocalPlan("别睡了，起来挥挥手")!, window.ConversationRevision);
            if (drawing.BedScene is not null) { Check(drawing.BedScene.WakeRequested, "wake-and-wave first requests actual wake scene"); AdvanceBed(40); }
            Expire(); Check(drawing.Action == "wave", "wake-and-wave executes waving after leaving bed");
            Expire();
            window.Animate("emotion:happy"); window.Thinking(true);
            Check(drawing.Action == "idle" && drawing.Emotion == "happy", "thinking indicator does not overwrite an explicit expression");
            Check((double)Field("actionUntil").GetValue(window)! >= 15, "ordinary expressions retain their pose for at least fifteen seconds");
            window.Animate("hold"); Expire();
            Check(drawing.Emotion == "happy" && (string)Field("heldState").GetValue(window)! == "emotion:happy", "explicitly held expression survives expired clip timer");
            window.InterruptConversation(preserveState: true); window.Thinking(true);
            window.ReactToConversation(new("你好", "curious", ["wave"]), window.ConversationRevision);
            Check(drawing.Emotion == "happy", "ordinary conversation reactions cannot replace a held expression");
            window.Animate("walk"); Expire();
            Check(drawing.Action == "walk", "explicit walking survives clip expiry");
            window.Left = 0; var area = (System.Windows.Rect)typeof(PetWindow).GetProperty("Area", BindingFlags.Instance | BindingFlags.NonPublic)!.GetValue(window)!;
            window.Left = area.Right - window.Width; Set("strollDirection", 1); AdvanceWalking(1);
            Check(drawing.Action == "idle" && (double)Field("velocityX").GetValue(window)! == 0, "walking pauses at the edge before changing direction");
            AdvanceWalking(5);
            Check((double)Field("velocityX").GetValue(window)! < 0, "walking rests before restarting inward at desktop boundary");
            window.InterruptConversation(preserveState: true); window.Thinking(true);
            window.ReactToConversation(new("我在呢", "happy", []), window.ConversationRevision); Expire();
            Check(drawing.Action == "walk", "new ordinary message and response preserve walking");
            window.Animate("sleep"); window.InterruptConversation(preserveState: true);
            window.ReactToConversation(new("听到啦", "happy", ["wave"]), window.ConversationRevision); Expire();
            Check(drawing.Action == "sleep", "ordinary conversation does not wake sleeping pet");
            window.ReactToConversation(new("起来啦", "neutral", ["idle"], Requested: true), window.ConversationRevision);
            if (drawing.BedScene is not null) AdvanceBed(40);
            store.Data.Wander = true; Set("nextDecision", -1d); Expire();
            Check(drawing.Action == "idle" && (string)Field("heldState").GetValue(window)! == "idle", "wake/stop state cannot be overwritten by autonomous wandering");
            window.Animate("free"); Set("nextDecision", -1d); Expire();
            Check(drawing.Action == "walk" && (string)Field("heldState").GetValue(window)! == "", "free mode restores bounded autonomous walking");
            store.Data.Wander = false; AdvanceWalking(10); Check(drawing.Action == "idle", "autonomous walk stops after its bounded stroll");
            window.Animate("walk"); window.InterruptConversation();
            Check((string)Field("heldState").GetValue(window)! == "" && drawing.Action == "idle", "physical/manual interrupt clears sustained mode");
            if (LuluBedScene.Available)
            {
                window.Left = area.Right - window.Width;
                double edge = window.Left;
                window.Animate("sleep");
                Check(drawing.BedApproaching && drawing.BedScene is null && window.Left == edge, "near right edge starts walking to room without teleporting or mirroring");
                AdvanceBed(.1);
                Check(window.Left == edge, "room-making does not slide the pet while its entry pose is turning");
                AdvanceBed(.6);
                Check(window.Left < edge && edge - window.Left <= 7.01, "room-making approach moves continuously");
                AdvanceBed(10);
                Check(drawing.BedScene is not null && !drawing.BedApproaching && window.Left + window.Width <= area.Right + .01, "bed scene fits the screen and retains left-to-right choreography");
                double beforeMeal = store.Data.Fullness;
                window.Animate("eat"); window.Animate("eat");
                Check(store.Data.Fullness == beforeMeal && drawing.BedScene!.WakeRequested, "new action waits for waking and is not performed behind the sleeping scene");
                AdvanceBed(40);
                Check(drawing.BedScene is null && drawing.Action == "eat" && store.Data.Fullness == beforeMeal + 20 && window.Width == window.Height, "latest queued action starts exactly once after walking away and bed exit");
                window.Animate("sleep"); AdvanceBed(10);
                typeof(PetWindow).GetMethod("CancelBedScene", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(window, null);
                window.InterruptConversation();
                Check(drawing.BedScene is null && !drawing.BedApproaching && window.Width == window.Height, "physical interruption releases bed scene and restores normal window bounds");
            }
            foreach (var name in ConversationBehavior.Actions.Concat(ConversationBehavior.Emotions).Where(n => n is not ("neutral" or "come" or "down" or "climb" or "hold" or "free")))
                Check(LuluVideo.Clips.ContainsKey(name), "behavior maps to installed video: " + name);
            log.Add("All runtime checks passed; isolated temporary store, no model requests or user data.");
            return 0;
        }
        catch (Exception error) { log.Add("FAIL " + error); return 1; }
        finally
        {
            if (window is not null) { Set("closing", true); window.Close(); }
            File.WriteAllLines(Path.Combine(AppContext.BaseDirectory, "conversation-check-results.txt"), log);
            if (Directory.Exists(directory)) Directory.Delete(directory, true);
        }
    }

    internal static void Run(Action<bool, string> check)
    {
        const string words = "好呀，\"挥挥手\"～\n送你🍉，路径 C:\\Lulu";
        string raw = JsonSerializer.Serialize(new { text = words, emotion = "happy", actions = new[] { "wave", "nod" } });
        foreach (var envelope in new[] { raw, "```json\n" + raw + "\n```" })
        {
            for (int i = 0; i <= envelope.Length; i++)
            {
                string shown = ConversationBehavior.DisplayText(envelope[..i]);
                if (!words.StartsWith(shown, StringComparison.Ordinal)) throw new Exception("Streaming leaked metadata or damaged an escape at " + i);
            }
            check(ConversationBehavior.DisplayText(envelope) == words, "streaming JSON hides control fields and decodes Unicode, emoji, quotes, newlines and backslashes");
        }
        var parsed = ConversationBehavior.Parse(raw, "我考试通过啦");
        check(parsed.Text == words && parsed.Emotion == "happy" && parsed.Actions.SequenceEqual(new[] { "wave", "nod" }), "context reply produces validated actions and expression");
        check(ConversationBehavior.Parse(raw, "今天特别开心").Emotion == "happy", "positive words containing bie are not mistaken for a negation");
        foreach (var input in new[] { "不要挥手", "别跳舞", "给我讲个挥手的故事", "他说想吃西瓜", "如果我让你跳舞", "翻译：吃西瓜", "昨天我们一起玩球", "你说过“吃西瓜”" })
        {
            var guarded = ConversationBehavior.Parse(raw, input);
            check(guarded.Actions.Length == 0 && guarded.Emotion == "neutral", "conservative negation/quotation/story guard: " + input);
        }
        var handled = ConversationBehavior.Parse("{\"text\":\"好呀\",\"emotion\":\"happy\",\"actions\":[\"eat\"]}", "吃西瓜", true);
        check(handled.Actions.Length == 0 && handled.Emotion == "neutral", "local command cannot feed or react twice");
        var duplicate = ConversationBehavior.Parse("{\"text\":\"好呀\",\"emotion\":\"happy\",\"actions\":[\"eat\",\"eat\"]}", "给你一块西瓜");
        check(duplicate.Actions.SequenceEqual(new[] { "eat" }), "duplicate feed is deduplicated");
        foreach (var bad in new[] {
            "{\"text\":\"你好\",\"emotion\":\"happy\",\"actions\":[\"delete_files\"]}",
            "{\"text\":\"你好\",\"emotion\":{},\"actions\":[]}",
            "{\"text\":\"你好\",\"emotion\":\"happy\",\"actions\":[\"wave\",\"nod\",\"eat\",\"play\",\"spin\",\"roll\",\"sleep\"]}",
            "{\"text\":\"你好\",\"emotion\":\"happy\",\"actions\":[1]}",
            "{\"text\":\"你好\",\"emotion\":\"happy\",\"actions\":[\"eat\"]",
            "你好" })
        {
            var fallback = ConversationBehavior.Parse(bad, "给你西瓜");
            check(!fallback.Structured && fallback.Text == "你好" && fallback.Actions.Length == 0 && fallback.Emotion == "neutral", "invalid/unsupported response falls back to text without execution");
        }
        var sleeping = ConversationBehavior.Parse("{\"text\":\"晚安\",\"emotion\":\"happy\",\"actions\":[\"sleep\",\"wave\"]}", "去休息吧");
        check(sleeping.Actions.SequenceEqual(new[] { "sleep" }) && sleeping.Emotion == "neutral", "sleep is terminal and does not get woken by an expression");
        var playback = new ConversationPlayback();
        int revision = playback.Revision;
        check(playback.Start(parsed, revision) && playback.Next() == "wave" && playback.Next() == "nod" && playback.Next() == "emotion:happy" && playback.Next() is null && !playback.Playing, "actions then expression complete in order");
        check(!playback.Start(parsed, revision), "same completed turn cannot execute again");
        revision = playback.Revision; playback.Interrupt();
        check(!playback.Start(parsed, revision), "late model response cannot override drag/stop/new interaction");
        check(playback.Start(parsed, playback.Revision), "next current turn can start");
        _ = playback.Next(); playback.Interrupt();
        check(playback.Next() is null && !playback.Playing, "interrupt removes every remaining action and expression");
        check(Commands.Action("别跳了") == "idle" && Commands.Action("停一下") == "idle", "short stop commands are immediate");
        check(Commands.Action("保持这个表情") == "hold" && Commands.Action("恢复自由活动") == "free" && Commands.Action("站住") == "idle" && Commands.Action("持续散步") == "walk" && Commands.Action("走走停停") == "walk", "sustained-state commands work without a model");
        var held = ConversationBehavior.Parse("{\"text\":\"好呀\",\"emotion\":\"angry\",\"actions\":[],\"intent\":\"request\",\"hold\":true}", "保持生气直到我叫停");
        check(held.Hold && held.Requested && held.Emotion == "angry", "explicit request can hold an expression");
        var unsolicited = ConversationBehavior.Parse("{\"text\":\"好呀\",\"emotion\":\"angry\",\"actions\":[],\"intent\":\"reaction\",\"hold\":true}", "今天怎么样");
        check(!unsolicited.Hold && !unsolicited.Requested, "ordinary reaction cannot request indefinite hold");

        // Exercise both existing provider SSE formats through the same stream filter and parser.
        foreach (bool claude in new[] { false, true })
        {
            var sse = new StringBuilder();
            foreach (char c in raw)
            {
                object chunk = claude ? new { type = "content_block_delta", delta = new { type = "text_delta", text = c.ToString() } } :
                    new { choices = new[] { new { delta = new { content = c.ToString() } } } };
                sse.Append("data: ").Append(JsonSerializer.Serialize(chunk)).Append("\n\n");
            }
            sse.Append(claude ? "data: {\"type\":\"message_stop\"}\n\n" : "data: [DONE]\n\n");
            string result = CloudClient.ReadSse(new StringReader(sse.ToString()), partial =>
            {
                if (!words.StartsWith(ConversationBehavior.DisplayText(partial), StringComparison.Ordinal)) throw new Exception("SSE metadata leak");
            }, default, claude).GetAwaiter().GetResult();
            check(ConversationBehavior.Parse(result, "开心一下").Actions.Length == 2, claude ? "Claude SSE -> clean text + behavior" : "OpenAI-compatible SSE -> clean text + behavior");
        }
    }
}
