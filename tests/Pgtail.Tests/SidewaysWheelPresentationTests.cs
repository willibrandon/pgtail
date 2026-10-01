using System.Text;
using Pgtail.Cli;

namespace Pgtail.Tests;

/// <summary>
/// The console input pgtail's full screens read, with the sideways wheel reported as the wheel with Shift held.
/// </summary>
[TestClass]
public sealed class SidewaysWheelPresentationTests
{
    /// <summary>
    /// A swipe left is reported as Shift with the wheel up, and a swipe right as Shift with the wheel down.
    /// </summary>
    [TestMethod]
    public void SidewaysWheelBecomesShiftWheel()
    {
        Assert.AreEqual("\e[<68;5;7M", Translate("\e[<66;5;7M", out int held));
        Assert.AreEqual(0, held);
        Assert.AreEqual("\e[<69;120;40M", Translate("\e[<67;120;40M", out held));
        Assert.AreEqual(0, held);
    }

    /// <summary>
    /// Modifiers held during the swipe are kept.
    /// </summary>
    [TestMethod]
    public void SidewaysWheelKeepsModifiers()
    {
        Assert.AreEqual("\e[<84;5;7M", Translate("\e[<82;5;7M", out _));
        Assert.AreEqual("\e[<77;5;7M", Translate("\e[<75;5;7M", out _));
    }

    /// <summary>
    /// The text around a swipe is passed on as it came.
    /// </summary>
    [TestMethod]
    public void TextAroundSidewaysWheelIsKept()
    {
        Assert.AreEqual("a\e[<69;1;1Mb\e[<68;2;2Mc", Translate("a\e[<67;1;1Mb\e[<66;2;2Mc", out int held));
        Assert.AreEqual(0, held);
    }

    /// <summary>
    /// Keys, clicks, and the wheel turned up and down are left alone.
    /// </summary>
    [TestMethod]
    public void OtherInputIsUnchanged()
    {
        foreach (string input in new[] { "abc", "\e[<0;5;7M", "\e[<0;5;7m", "\e[<64;5;7M", "\e[<69;5;7M", "\e[A", "\e" })
        {
            Assert.IsNull(SidewaysWheelPresentation.Translate(Encoding.ASCII.GetBytes(input), out int held), input);
            Assert.AreEqual(0, held, input);
        }
    }

    /// <summary>
    /// A report cut off at the end of a read is held, and rewritten once the rest of it arrives.
    /// </summary>
    [TestMethod]
    public void SplitReportIsHeldUntilComplete()
    {
        byte[] first = Encoding.ASCII.GetBytes("x\e[<67;1");
        Assert.IsNull(SidewaysWheelPresentation.Translate(first, out int held));
        Assert.AreEqual(7, held);
        Assert.AreEqual("\e[<69;10;3M", Translate("\e[<67;10;3M", out held));
        Assert.AreEqual(0, held);
    }

    /// <summary>
    /// Bytes that start like a report but are not one are passed on rather than held.
    /// </summary>
    [TestMethod]
    public void BrokenReportIsPassedOn()
    {
        Assert.AreEqual("\e[<x\e[<69;1;1M", Translate("\e[<x\e[<67;1;1M", out int held));
        Assert.AreEqual(0, held);
    }

    private static string? Translate(string input, out int held) =>
        SidewaysWheelPresentation.Translate(Encoding.ASCII.GetBytes(input), out held) is { } output
            ? Encoding.ASCII.GetString(output)
            : null;
}
