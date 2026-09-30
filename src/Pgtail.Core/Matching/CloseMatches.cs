namespace Pgtail.Matching;

/// <summary>
/// Suggests the closest known word for a misspelled one, as Python's <c>difflib.get_close_matches</c> does.
/// </summary>
public static class CloseMatches
{
    /// <summary>
    /// The candidate most similar to a word, when similar enough.
    /// </summary>
    /// <remarks>
    /// Similarity is the Ratcliff/Obershelp ratio: twice the characters in matching blocks over the total length.
    /// </remarks>
    /// <param name="word">The word typed.</param>
    /// <param name="candidates">The known words.</param>
    /// <param name="cutoff">The least ratio accepted, from 0 to 1.</param>
    /// <returns>The best candidate, or null.</returns>
    public static string? Best(string word, IEnumerable<string> candidates, double cutoff = 0.6)
    {
        ArgumentNullException.ThrowIfNull(word);
        ArgumentNullException.ThrowIfNull(candidates);
        string? best = null;
        double bestRatio = cutoff;
        foreach (string candidate in candidates)
        {
            double ratio = Ratio(word, candidate);
            if (ratio > bestRatio || (ratio == bestRatio && best is null && ratio >= cutoff))
            {
                best = candidate;
                bestRatio = ratio;
            }
        }

        return best;
    }

    /// <summary>
    /// The Ratcliff/Obershelp similarity of two strings.
    /// </summary>
    /// <param name="a">One string.</param>
    /// <param name="b">The other.</param>
    /// <returns>The ratio, from 0 to 1.</returns>
    public static double Ratio(string a, string b)
    {
        ArgumentNullException.ThrowIfNull(a);
        ArgumentNullException.ThrowIfNull(b);
        int total = a.Length + b.Length;
        return total == 0 ? 1 : 2.0 * Matches(a, 0, a.Length, b, 0, b.Length) / total;
    }

    private static int Matches(string a, int aStart, int aEnd, string b, int bStart, int bEnd)
    {
        (int i, int j, int size) = LongestMatch(a, aStart, aEnd, b, bStart, bEnd);
        if (size == 0)
        {
            return 0;
        }

        return size + Matches(a, aStart, i, b, bStart, j) + Matches(a, i + size, aEnd, b, j + size, bEnd);
    }

    private static (int I, int J, int Size) LongestMatch(string a, int aStart, int aEnd, string b, int bStart, int bEnd)
    {
        (int I, int J, int Size) best = (I: aStart, J: bStart, Size: 0);
        for (int i = aStart; i < aEnd; i++)
        {
            for (int j = bStart; j < bEnd; j++)
            {
                int size = 0;
                while (i + size < aEnd && j + size < bEnd && a[i + size] == b[j + size])
                {
                    size++;
                }

                if (size > best.Size)
                {
                    best = (i, j, size);
                }
            }
        }

        return best;
    }
}
