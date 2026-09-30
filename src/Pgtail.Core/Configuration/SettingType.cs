namespace Pgtail.Configuration;

/// <summary>
/// How a setting's value is typed on the command line.
/// </summary>
public enum SettingType
{
    /// <summary>
    /// <c>true</c>, <c>1</c>, or <c>yes</c> for true; anything else for false.
    /// </summary>
    Boolean,

    /// <summary>
    /// A whole number.
    /// </summary>
    WholeNumber,

    /// <summary>
    /// One or more words, each an item.
    /// </summary>
    List,

    /// <summary>
    /// Text; several words are joined with spaces.
    /// </summary>
    Text,
}
