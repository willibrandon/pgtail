using System.Globalization;
using System.Net.Http.Headers;
using System.Text.Json;
using Pgtail.Configuration;
using Pgtail.Styling;

namespace Pgtail.Updates;

/// <summary>
/// Checks GitHub for a newer release: at startup at most once a day, or on demand with <c>--check-update</c>.
/// </summary>
/// <param name="currentVersion">The running version, such as <c>0.6.1</c>.</param>
/// <param name="upgradeCommand">The command or page that upgrades this installation.</param>
public sealed class UpdateChecker(string currentVersion, string upgradeCommand)
{
    /// <summary>
    /// The latest release endpoint.
    /// </summary>
    public const string ReleasesUrl = "https://api.github.com/repos/willibrandon/pgtail/releases/latest";

    private static readonly TimeSpan s_timeout = TimeSpan.FromSeconds(5);
    private static readonly TimeSpan s_interval = TimeSpan.FromHours(24);

    /// <summary>
    /// Fetches the latest release's version.
    /// </summary>
    /// <param name="cancellationToken">Cancels the request.</param>
    /// <returns>The version without its <c>v</c> prefix, or null when GitHub could not be reached or answered oddly.</returns>
    public async Task<string?> FetchLatestAsync(CancellationToken cancellationToken)
    {
        using var client = new HttpClient { Timeout = s_timeout };
        using var request = new HttpRequestMessage(HttpMethod.Get, ReleasesUrl);
        request.Headers.Accept.Add(new MediaTypeWithQualityHeaderValue("application/vnd.github+json"));
        request.Headers.UserAgent.Add(new ProductInfoHeaderValue("pgtail", currentVersion));
        try
        {
            using HttpResponseMessage response = await client.SendAsync(request, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                return null;
            }

            await using Stream stream = await response.Content.ReadAsStreamAsync(cancellationToken);
            using JsonDocument document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
            return document.RootElement.TryGetProperty("tag_name", out JsonElement tag) && tag.GetString() is { Length: > 0 } name
                ? name.TrimStart('v')
                : null;
        }
        catch (Exception exception) when (exception is HttpRequestException or TaskCanceledException or JsonException
            or InvalidOperationException)
        {
            return null;
        }
    }

    /// <summary>
    /// Whether a version is newer than the running one; a development build is older than every release.
    /// </summary>
    /// <param name="latest">The latest release's version.</param>
    /// <returns>True when an upgrade is available.</returns>
    public bool IsNewer(string latest)
    {
        ArgumentNullException.ThrowIfNull(latest);
        if (currentVersion.EndsWith("-dev", StringComparison.Ordinal))
        {
            return true;
        }

        return Version.TryParse(Numeric(latest), out Version? next) && Version.TryParse(Numeric(currentVersion), out Version? current)
            ? next > current
            : string.CompareOrdinal(latest, currentVersion) > 0;
    }

    /// <summary>
    /// Whether the startup check is due: checks are on and a day has passed since the last one.
    /// </summary>
    /// <param name="config">The settings.</param>
    /// <param name="now">The current time in UTC.</param>
    /// <returns>True to check.</returns>
    public static bool ShouldCheck(PgtailConfig config, DateTime now)
    {
        ArgumentNullException.ThrowIfNull(config);
        if (!config.UpdatesCheck)
        {
            return false;
        }

        return !DateTimeOffset.TryParse(config.LastUpdateCheck, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal,
                out DateTimeOffset last)
            || now - last.UtcDateTime >= s_interval;
    }

    /// <summary>
    /// The startup notice: <c>pgtail X available. Upgrade with: ...</c>.
    /// </summary>
    /// <param name="latest">The latest version.</param>
    /// <returns>The styled notice.</returns>
    public StyledText Notice(string latest) => new StyledText("pgtail ").Append(latest, StyleParser.Parse("bold")).Append(" ")
        .Append("available", StyleParser.Parse("green")).Append(". Upgrade with: ").Append(upgradeCommand, StyleParser.Parse("cyan"));

    /// <summary>
    /// The <c>--check-update</c> result.
    /// </summary>
    /// <param name="latest">The latest version, or null when the check failed.</param>
    /// <returns>The styled message.</returns>
    public StyledText Report(string? latest)
    {
        if (latest is null)
        {
            return new StyledText("Unable to check for updates. Check your network connection.");
        }

        return IsNewer(latest)
            ? new StyledText("pgtail ").Append(latest, StyleParser.Parse("bold")).Append(" is ").Append("available",
                StyleParser.Parse("green"))
                .Append($" (current: {currentVersion}). Upgrade with: ").Append(upgradeCommand, StyleParser.Parse("cyan"))
            : new StyledText($"pgtail {currentVersion} is up to date.");
    }

    private static string Numeric(string version)
    {
        int end = version.IndexOfAny(['-', '+']);
        return end >= 0 ? version[..end] : version;
    }
}
