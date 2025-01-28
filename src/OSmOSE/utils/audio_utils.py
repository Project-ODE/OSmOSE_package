from pathlib import Path

import pandas as pd
import soundfile as sf

from OSmOSE.config import (
    AUDIO_METADATA,
    BUILD_DURATION_DELTA_THRESHOLD,
    SUPPORTED_AUDIO_FORMAT,
)


def is_supported_audio_format(filename: Path) -> bool:
    """Check if a given file is a supported audio file based on its extension.

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
    return filename.suffix.lower() in SUPPORTED_AUDIO_FORMAT


def get_all_audio_files(directory: Path) -> list[Path]:
    """Retrieve all supported audio files from a given directory.

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
    return sorted(
        file
        for extension in SUPPORTED_AUDIO_FORMAT
        for file in directory.glob(f"*{extension}")
    )


def get_audio_metadata(audio_file: Path) -> dict:
    """Read metadata from the audio file.

    Parameters
    ----------
    audio_file: pathlib.Path
        The path to the audio file.

    Returns
    -------
    dict:
        A dictionary containing the metadata of the audio file.
        The metadata list is grabbed from OSmOSE.config.AUDIO_METADATA.

    """
    with sf.SoundFile(audio_file, "r") as af:
        return {key: f(af) for key, f in AUDIO_METADATA.items()}


def check_audio(
    audio_metadata: pd.DataFrame,
    timestamps: pd.DataFrame,
) -> None:
    """Raise errors if the audio files present anomalies.

    Parameters
    ----------
    audio_metadata: pandas.DataFrame
        metadata of the audio files
    timestamps: pandas.DataFrame
        timestamps of the audio files

    Raises
    ------
    FileNotFoundError:
        If the number of audio files doesn't match the number of timestamps.
    ValueError:
        If the audio files present one of the following anomalies:
        - Different sampling rates among audio files
        - Large duration differences (> 5% of the mean duration) among audio files

    """
    if (
        len(
            unlisted_files := [
                file
                for file in audio_metadata["filename"]
                if file not in timestamps["filename"].unique()
            ],
        )
        > 0
    ):
        message = (
            "The following files have not been found in timestamp.csv:\n\t"
            + "\n\t".join(unlisted_files)
        )
        raise FileNotFoundError(message)

    if (
        len(
            missing_files := [
                file
                for file in timestamps["filename"]
                if file not in audio_metadata["filename"].unique()
            ],
        )
        > 0
    ):
        message = (
            "The following files are listed in timestamp.csv but hasn't be found:\n\t"
            + "\n\t".join(missing_files)
        )
        raise FileNotFoundError(message)

    if len(sample_rates := audio_metadata["origin_sr"].unique()) > 1:
        message = (
            "Your files do not have all the same sampling rate.\n"
            f"Found sampling rates: {', '.join(str(sr) + ' Hz' for sr in sample_rates)}."
        )
        raise ValueError(message)

    mean_duration = audio_metadata["duration"].mean()
    if any(
        abs(mean_duration - d) > BUILD_DURATION_DELTA_THRESHOLD * mean_duration
        for d in audio_metadata["duration"].unique()
    ):
        message = "Your audio files have large duration discrepancies."
        raise ValueError(message)
