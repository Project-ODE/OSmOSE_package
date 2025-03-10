"""SpectroDataset is a collection of SpectroData objects.

SpectroDataset is a collection of SpectroData, with methods
that simplify repeated operations on the spectro data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytz
from scipy.signal import ShortTimeFFT

from OSmOSE.core_api.base_dataset import BaseDataset
from OSmOSE.core_api.json_serializer import deserialize_json
from OSmOSE.core_api.spectro_data import SpectroData
from OSmOSE.core_api.spectro_file import SpectroFile

if TYPE_CHECKING:
    from pathlib import Path

    from pandas import Timedelta, Timestamp

    from OSmOSE.core_api.audio_dataset import AudioDataset


class SpectroDataset(BaseDataset[SpectroData, SpectroFile]):
    """SpectroDataset is a collection of SpectroData objects.

    SpectroDataset is a collection of SpectroData, with methods
    that simplify repeated operations on the spectro data.

    """

    def __init__(self, data: list[SpectroData]) -> None:
        """Initialize a SpectroDataset."""
        super().__init__(data)

    @property
    def fft(self) -> ShortTimeFFT:
        """Return the fft of the spectro data."""
        return next(data.fft for data in self.data)

    @fft.setter
    def fft(self, fft: ShortTimeFFT) -> None:
        for data in self.data:
            data.fft = fft

    def save_spectrogram(self, folder: Path) -> None:
        """Export all spectrogram data as png images in the specified folder.

        Parameters
        ----------
        folder: Path
            Folder in which the spectrograms should be saved.

        """
        for data in self.data:
            data.save_spectrogram(folder)

    def to_dict(self) -> dict:
        """Serialize a SpectroDataset to a dictionary.

        Returns
        -------
        dict:
            The serialized dictionary representing the SpectroDataset.

        """
        sft_dict = {}
        for data in self.data:
            sft = next(
                (
                    sft
                    for name, sft in sft_dict.items()
                    if np.array_equal(data.fft.win, sft["win"])
                    and data.fft.hop == sft["hop"]
                    and data.fft.fs == sft["fs"]
                    and data.fft.mfft == sft["mfft"]
                ),
                None,
            )
            if sft is None:
                sft_dict[str(data.fft)] = {
                    "win": list(data.fft.win),
                    "hop": data.fft.hop,
                    "fs": data.fft.fs,
                    "mfft": data.fft.mfft,
                    "spectro_data": [str(data)],
                }
                continue
            sft["spectro_data"].append(str(data))
        spectro_data_dict = {str(d): d.to_dict(embed_sft=False) for d in self.data}
        return {"data": spectro_data_dict} | {"sft": sft_dict}

    @classmethod
    def from_dict(cls, dictionary: dict) -> SpectroDataset:
        """Deserialize a SpectroDataset from a dictionary.

        Parameters
        ----------
        dictionary: dict
            The serialized dictionary representing the SpectroDataset.

        Returns
        -------
        AudioData
            The deserialized SpectroDataset.

        """
        sfts = [
            (
                ShortTimeFFT(
                    win=np.array(sft["win"]),
                    hop=sft["hop"],
                    fs=sft["fs"],
                    mfft=sft["mfft"],
                ),
                sft["spectro_data"],
            )
            for name, sft in dictionary["sft"].items()
        ]
        sd = [
            SpectroData.from_dict(
                params,
                sft=next(sft for sft, linked_data in sfts if name in linked_data),
            )
            for name, params in dictionary["data"].items()
        ]
        return cls(sd)

    @classmethod
    def from_folder(
        cls,
        folder: Path,
        strptime_format: str,
        begin: Timestamp | None = None,
        end: Timestamp | None = None,
        timezone: str | pytz.timezone | None = None,
        data_duration: Timedelta | None = None,
        **kwargs: any,
    ) -> SpectroDataset:
        """Return a SpectroDataset from a folder containing the audio files.

        Parameters
        ----------
        folder: Path
            The folder containing the spectro files.
        strptime_format: str
            The strptime format of the timestamps in the spectro file names.
        begin: Timestamp | None
            The begin of the spectro dataset.
            Defaulted to the begin of the first file.
        end: Timestamp | None
            The end of the spectro dataset.
            Defaulted to the end of the last file.
        timezone: str | pytz.timezone | None
            The timezone in which the file should be localized.
            If None, the file begin/end will be tz-naive.
            If different from a timezone parsed from the filename, the timestamps'
            timezone will be converted from the parsed timezone
            to the specified timezone.
        data_duration: Timedelta | None
            Duration of the spectro data objects.
            If provided, spectro data will be evenly distributed between begin and end.
            Else, one data object will cover the whole time period.
        kwargs: any
            Keyword arguments passed to the BaseDataset.from_folder classmethod.

        Returns
        -------
        Spectrodataset:
            The audio dataset.

        """
        kwargs.update(
            {"file_class": SpectroFile, "supported_file_extensions": [".npz"]},
        )
        base_dataset = BaseDataset.from_folder(
            folder=folder,
            strptime_format=strptime_format,
            begin=begin,
            end=end,
            timezone=timezone,
            data_duration=data_duration,
            **kwargs,
        )
        sft = next(iter(base_dataset.files)).get_fft()
        return cls.from_base_dataset(base_dataset, sft)

    @classmethod
    def from_base_dataset(
        cls,
        base_dataset: BaseDataset,
        fft: ShortTimeFFT,
    ) -> SpectroDataset:
        """Return a SpectroDataset object from a BaseDataset object."""
        return cls(
            [SpectroData.from_base_data(data, fft) for data in base_dataset.data],
        )

    @classmethod
    def from_audio_dataset(
        cls,
        audio_dataset: AudioDataset,
        fft: ShortTimeFFT,
    ) -> SpectroDataset:
        """Return a SpectroDataset object from an AudioDataset object.

        The SpectroData is computed from the AudioData using the given fft.
        """
        return cls([SpectroData.from_audio_data(d, fft) for d in audio_dataset.data])

    @classmethod
    def from_json(cls, file: Path) -> SpectroDataset:
        """Deserialize a SpectroDataset from a JSON file.

        Parameters
        ----------
        file: Path
            Path to the serialized JSON file representing the SpectroDataset.

        Returns
        -------
        SpectroDataset
            The deserialized SpectroDataset.

        """
        # I have to redefine this method (without overriding it)
        # for the type hint to be correct.
        # It seems to be due to BaseData being a Generic class, following which
        # AudioData.from_json() is supposed to return a BaseData
        # without this duplicate definition...
        # I might look back at all this in the future
        return cls.from_dict(deserialize_json(file))
