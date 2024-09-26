from OSmOSE.config import SUPPORTED_AUDIO_FORMAT
from pathlib import Path


def is_audio(filename: Path) -> bool:
    """
    Check if a given file is a supported audio file based on its extension.

    Parameters
    ----------
    filename : Path
        The path to the file to be checked.

    Returns
    -------
    bool
        True if the file has an extension that matches a supported audio format,
        False otherwise.
    """
    return filename.suffix in SUPPORTED_AUDIO_FORMAT


def get_audio_file(directory: Path) -> list[Path]:
    """
    Retrieve all supported audio files from a given directory.

    Parameters
    ----------
    file_path : Path
        The path to the directory to search for audio files

    Returns
    -------
    list[Path]
        A list of `Path` objects corresponding to the supported audio files
        found in the directory.
    """
    audio_path = []
    for ext in SUPPORTED_AUDIO_FORMAT:
        audio_path.extend(list(directory.glob(f"*{ext}")))

    return sorted(audio_path)
