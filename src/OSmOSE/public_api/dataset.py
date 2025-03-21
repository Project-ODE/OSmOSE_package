"""Main class of the Public API.

The Dataset correspond to a collection of audio,
spectro and auxilary core_api datasets.
It has additionnal metadata that can be exported, e.g. to APLOSE.

"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from OSmOSE.core_api.audio_dataset import AudioDataset
from OSmOSE.core_api.base_dataset import BaseDataset
from OSmOSE.core_api.json_serializer import deserialize_json, serialize_json
from OSmOSE.core_api.spectro_dataset import SpectroDataset
from OSmOSE.utils.path_utils import move_tree

if TYPE_CHECKING:
    from pandas import Timedelta, Timestamp

    from OSmOSE.core_api.audio_file import AudioFile


class Dataset:
    """Main class of the Public API.

    The Dataset correspond to a collection of audio,
    spectro and auxilary core_api datasets.
    It has additionnal metadata that can be exported, e.g. to APLOSE.

    """

    def __init__(  # noqa: PLR0913
        self,
        folder: Path,
        strptime_format: str,
        gps_coordinates: str | list | tuple = (0, 0),
        depth: str | int = 0,
        timezone: str | None = None,
        datasets: dict | None = None,
    ) -> None:
        """Initialize a Dataset."""
        self.folder = folder
        self.strptime_format = strptime_format
        self.gps_coordinates = gps_coordinates
        self.depth = depth
        self.timezone = timezone
        self.datasets = datasets if datasets is not None else {}

    @property
    def origin_files(self) -> set[AudioFile]:
        """Return the original audio files from which this Dataset has been built."""
        return None if self.origin_dataset is None else self.origin_dataset.files

    @property
    def origin_dataset(self) -> AudioDataset:
        """Return the AudioDataset from which this Dataset has been built."""
        return (
            None
            if "original" not in self.datasets
            else self.datasets["original"]["dataset"]
        )

    def build(self) -> None:
        """Build the Dataset.

        Building a dataset moves the original audio files to a specific folder
        and creates metadata csv used by APLOSE.

        """
        ads = AudioDataset.from_folder(
            self.folder,
            strptime_format=self.strptime_format,
            bound="files",
        )
        self.datasets["original"] = {"class": type(ads).__name__, "dataset": ads}
        move_tree(
            self.folder,
            self.folder / "other",
            {file.path for file in self.datasets["original"]["dataset"].files},
        )
        self._sort_dataset(self.datasets["original"]["dataset"])
        ads.write_json(ads.folder)
        self.write_json()

    def reset(self) -> None:
        """Reset the Dataset.

        Resetting a dataset will move back the original audio files and the content of
        the "other" folder to the root folder.
        WARNING: all other files and folders will be deleted.
        """
        files_to_remove = list(self.folder.iterdir())
        self.datasets["original"]["dataset"].folder = self.folder

        if self.folder / "other" in files_to_remove:
            move_tree(self.folder / "other", self.folder)

        for file in files_to_remove:
            if file.is_dir():
                shutil.rmtree(file)
            else:
                file.unlink()

        self.datasets = {}

    def reshape(
        self,
        begin: Timestamp | None = None,
        end: Timestamp | None = None,
        data_duration: Timedelta | None = None,
        sample_rate: float | None = None,
        name: str | None = None,
    ) -> None:
        """Create and write a new AudioDataset from the original audio files.

        The parameters of this method allow for a reshaping and resampling
        of the audio data.
        The created AudioDataset's files will be written to disk along with
        a JSON serialized file.

        Parameters
        ----------
        begin: Timestamp | None
            The begin of the audio dataset.
            Defaulted to the begin of the original dataset.
        end: Timestamp | None
            The end of the audio dataset.
            Defaulted to the end of the original dataset.
        data_duration: Timedelta | None
            Duration of the audio data within the new dataset.
            If provided, audio data will be evenly distributed between begin and end.
            Else, one data object will cover the whole time period.
        sample_rate: float | None
            Sample rate of the new audio data.
            Audio data will be resampled if provided, else the sample rate
            will be set to the one of the original dataset.
        name: str | None
            Name of the new dataset.
            Defaulted as the begin timestamp of the new dataset.

        """
        ads = AudioDataset.from_files(
            files=list(self.origin_files),
            begin=begin,
            end=end,
            data_duration=data_duration,
        )

        if sample_rate is not None:
            ads.sample_rate = sample_rate

        ads_folder = self._get_audio_dataset_subpath(ads)
        ads.write(ads_folder, link=True)

        dataset_name = str(ads) if name is None else name
        self.datasets[dataset_name] = {"class": type(ads).__name__, "dataset": ads}

        ads.write_json(ads.folder)
        self.write_json()

    def _get_audio_dataset_subpath(self, dataset: AudioDataset) -> Path:
        data_duration = dataset.data_duration
        sample_rate = dataset.sample_rate
        data_duration, sample_rate = (
            parameter if type(parameter) is not set else next(iter(parameter))
            for parameter in (data_duration, sample_rate)
        )
        return (
            self.folder
            / "data"
            / "audio"
            / f"{round(data_duration.total_seconds())}_{round(sample_rate)}"
        )

    def _sort_dataset(self, dataset: type[DatasetChild]) -> None:
        if type(dataset) is AudioDataset:
            self._sort_audio_dataset(dataset)
            return
        if type(dataset) is SpectroDataset:
            self._sort_spectro_dataset(dataset)
            return

    def _sort_audio_dataset(self, dataset: AudioDataset) -> None:
        dataset.folder = self._get_audio_dataset_subpath(dataset)

    def _sort_spectro_dataset(self, dataset: SpectroDataset) -> None:
        pass

    def to_dict(self) -> dict:
        """Serialize a dataset to a dictionary.

        Returns
        -------
        dict:
            The serialized dictionary representing the dataset.

        """
        return {
            "datasets": {
                name: {
                    "class": dataset["class"],
                    "json": str(dataset["dataset"].serialized_file),
                }
                for name, dataset in self.datasets.items()
            },
            "depth": self.depth,
            "folder": str(self.folder),
            "gps_coordinates": self.gps_coordinates,
            "strptime_format": self.strptime_format,
            "timezone": self.timezone,
        }

    """
        folder: Path,
        strptime_format: str,
        gps_coordinates: str | list | tuple = (0, 0),
        depth: str | int = 0,
        timezone: str | None = None,
    """

    @classmethod
    def from_dict(cls, dictionary: dict) -> Dataset:
        """Deserialize a dataset from a dictionary.

        Parameters
        ----------
        dictionary: dict
            The serialized dictionary representing the dataset.

        Returns
        -------
        Dataset
            The deserialized dataset.

        """
        datasets = {}
        for name, dataset in dictionary["datasets"].items():
            dataset_class = (
                AudioDataset
                if dataset["class"] == "AudioDataset"
                else (
                    SpectroDataset
                    if dataset["class"] == "SpectroDataset"
                    else BaseDataset
                )
            )
            datasets[name] = {
                "class": dataset["class"],
                "dataset": dataset_class.from_json(Path(dataset["json"])),
            }
        return cls(
            folder=Path(dictionary["folder"]),
            strptime_format=dictionary["strptime_format"],
            gps_coordinates=dictionary["gps_coordinates"],
            depth=dictionary["depth"],
            timezone=dictionary["timezone"],
            datasets=datasets,
        )

    def write_json(self, folder: Path | None = None) -> None:
        """Write a serialized Dataset to a JSON file."""
        folder = folder if folder is not None else self.folder
        serialize_json(folder / "dataset.json", self.to_dict())

    @classmethod
    def from_json(cls, file: Path) -> Dataset:
        """Deserialize a Dataset from a JSON file.

        Parameters
        ----------
        file: Path
            Path to the serialized JSON file representing the Dataset.

        Returns
        -------
        Dataset
            The deserialized BaseDataset.

        """
        return cls.from_dict(deserialize_json(file))


DatasetChild = TypeVar("DatasetChild", bound=BaseDataset)
