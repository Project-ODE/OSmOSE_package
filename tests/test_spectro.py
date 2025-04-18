from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pytest
from pandas import Timedelta
from scipy.signal import ShortTimeFFT
from scipy.signal.windows import hamming

from OSmOSE.config import TIMESTAMP_FORMAT_EXPORTED_FILES, TIMESTAMP_FORMAT_TEST_FILES
from OSmOSE.core_api.audio_data import AudioData
from OSmOSE.core_api.audio_dataset import AudioDataset
from OSmOSE.core_api.audio_file import AudioFile
from OSmOSE.core_api.ltas_data import LTASData
from OSmOSE.core_api.spectro_data import SpectroData
from OSmOSE.core_api.spectro_dataset import SpectroDataset
from OSmOSE.core_api.spectro_file import SpectroFile
from OSmOSE.utils.audio_utils import generate_sample_audio

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("audio_files", "original_audio_data", "sft"),
    [
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 48_000,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            generate_sample_audio(1, 48_000, dtype=np.float64),
            ShortTimeFFT(hamming(1_024), 1024, 48_000),
            id="short_spectrogram",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            generate_sample_audio(1, 1_024, dtype=np.float64),
            ShortTimeFFT(hamming(1_024), 1024, 1_024),
            id="data_is_one_window_long",
        ),
    ],
    indirect=["audio_files"],
)
def test_spectrogram_shape(
    tmp_path: Path,
    audio_files: tuple[list[Path], pytest.fixtures.Subrequest],
    original_audio_data: list[np.ndarray],
    sft: ShortTimeFFT,
) -> None:
    dataset = AudioDataset.from_folder(
        tmp_path,
        strptime_format=TIMESTAMP_FORMAT_TEST_FILES,
    )
    spectro_dataset = SpectroDataset.from_audio_dataset(dataset, sft)
    for audio, spectro in zip(dataset.data, spectro_dataset.data):
        assert spectro.shape == spectro.get_value().shape
        assert spectro.shape == (sft.f.shape[0], sft.p_num(audio.shape))


@pytest.mark.parametrize(
    ("audio_files", "date_begin", "sft"),
    [
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 48_000,
                "nb_files": 1,
            },
            pd.Timestamp("2024-01-01 12:00:00"),
            ShortTimeFFT(hamming(1_024), 1024, 48_000),
            id="second_precision",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
            },
            pd.Timestamp("2024-01-01 12:00:00.123"),
            ShortTimeFFT(hamming(512), 512, 1_024),
            id="millisecond_precision",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 48_000,
                "nb_files": 1,
            },
            pd.Timestamp("2024-01-01 12:00:00.123456"),
            ShortTimeFFT(hamming(1_024), 1_024, 48_000),
            id="microsecond_precision",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 48_000,
                "nb_files": 1,
            },
            pd.Timestamp("2024-01-01 12:00:00.123456789"),
            ShortTimeFFT(hamming(1_024), 1_024, 48_000),
            id="nanosecond_precision",
        ),
        pytest.param(
            {
                "duration": 1.123456789,
                "sample_rate": 48_000,
                "nb_files": 1,
            },
            pd.Timestamp("2024-01-01 12:00:00.123456789"),
            ShortTimeFFT(hamming(1_024), 1_024, 48_000),
            id="nanosecond_precision_end",
        ),
    ],
    indirect=["audio_files"],
)
def test_spectro_parameters_in_npz_files(
    tmp_path: Path,
    audio_files: tuple[list[Path], pytest.fixtures.Subrequest],
    date_begin: pd.Timestamp,
    sft: ShortTimeFFT,
) -> None:

    af = next(AudioFile(f, begin=date_begin) for f in tmp_path.glob("*.wav"))

    ad = AudioData.from_files([af])
    sd = SpectroData.from_audio_data(ad, sft)
    sd.write(tmp_path / "npz")
    file = tmp_path / "npz" / f"{sd}.npz"
    sf = SpectroFile(file, strptime_format=TIMESTAMP_FORMAT_EXPORTED_FILES)

    assert sf.begin == ad.begin
    assert sf.end == ad.end
    assert np.array_equal(sf.freq, sft.f)
    assert sf.hop == sft.hop
    assert sf.mfft == sft.mfft
    assert sf.sample_rate == sft.fs
    nb_time_bins = sft.t(ad.shape).shape[0]
    assert np.array_equal(
        sf.time,
        np.arange(nb_time_bins) * ad.duration.total_seconds() / nb_time_bins,
    )


@pytest.mark.parametrize(
    ("audio_files", "nb_chunks", "sft"),
    [
        pytest.param(
            {
                "duration": 6,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            3,
            ShortTimeFFT(hamming(1_024), 1_024, 1_024),
            id="6_seconds_split_in_3",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            1,
            ShortTimeFFT(hamming(1_024), 100, 1_024),
            id="1_npz_file",
        ),
        pytest.param(
            {
                "duration": 6,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            3,
            ShortTimeFFT(hamming(1_024), 100, 1_024),
            id="6_seconds_split_in_3_with_overlap",
        ),
        pytest.param(
            {
                "duration": 8,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            4,
            ShortTimeFFT(hamming(1_024), 100, 1_024),
            id="8_seconds_split_in_4",
        ),
        pytest.param(
            {
                "duration": 4,
                "sample_rate": 48_000,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            4,
            ShortTimeFFT(hamming(12_000), 12_000, 48_000),
            id="high_sr_no_overlap",
        ),
        pytest.param(
            {
                "duration": 2,
                "sample_rate": 48_000,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            3,
            ShortTimeFFT(hamming(12_000), 10_000, 48_000),
            id="high_sr_overlap",
        ),
        pytest.param(
            {
                "duration": 6,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            6,
            ShortTimeFFT(hamming(1_024), 1_024, 1_024),
            id="6_seconds_split_in_6",
        ),
        pytest.param(
            {
                "duration": 6,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            6,
            ShortTimeFFT(hamming(1_024), 100, 1_024),
            id="6_seconds_split_in_6_with_overlap",
        ),
    ],
    indirect=["audio_files"],
)
def test_spectrogram_from_npz_files(
    tmp_path: Path,
    audio_files: tuple[list[Path], pytest.fixtures.Subrequest],
    nb_chunks: int,
    sft: ShortTimeFFT,
) -> None:
    afs = [
        AudioFile(f, strptime_format=TIMESTAMP_FORMAT_TEST_FILES)
        for f in tmp_path.glob("*.wav")
    ]

    ad = AudioData.from_files(afs)
    sd = SpectroData.from_audio_data(ad, sft)

    sd_split = sd.split(nb_chunks)

    import soundfile as sf

    for spectro in sd_split:
        spectro.write(tmp_path / "output")
        centered_data = spectro.audio_data.get_value(reject_dc=True)
        (tmp_path / "audio").mkdir(exist_ok=True)
        sf.write(
            file=tmp_path / "audio" / f"{spectro.audio_data}.wav",
            data=centered_data,
            samplerate=spectro.audio_data.sample_rate,
            subtype="DOUBLE",
        )

    assert len(list((tmp_path / "output").glob("*.npz"))) == nb_chunks

    # Since we reject the DC of audio data before computing Sx values of each chunk,
    # we must compare the concatenated chunks with an AudioData made from the
    # DC-free parts.

    afs = [
        AudioFile(f, strptime_format=TIMESTAMP_FORMAT_EXPORTED_FILES)
        for f in (tmp_path / "audio").glob("*.wav")
    ]
    ad = AudioData.from_files(afs)
    sd = SpectroData.from_audio_data(ad, sft)

    sds = SpectroDataset.from_folder(
        tmp_path / "output",
        TIMESTAMP_FORMAT_EXPORTED_FILES,
    )

    assert sds.begin == ad.begin

    # Beats me, but Timedelta.round() raises a DivideByZeroException if done
    # directly on the duration properties.

    dt1, dt2 = (Timedelta(str(dt)) for dt in (sds.duration, ad.duration))

    assert dt1.round(freq="ms") == dt2.round(freq="ms")
    assert len(sds.data) == 1
    assert sds.data[0].shape == sds.data[0].get_value().shape

    assert sds.data[0].shape == (
        sft.f.shape[0],
        sft.p_num(int(ad.duration.total_seconds() * ad.sample_rate)),
    )

    assert np.allclose(sd.get_value(), sds.data[0].get_value())


@pytest.mark.parametrize(
    ("audio_files", "origin_dtype", "target_dtype", "expected_value_dtype"),
    [
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            complex,
            complex,
            complex,
            id="complex_to_complex",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            complex,
            float,
            float,
            id="complex_to_float",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            complex,
            float,
            float,
            id="float_to_float",
        ),
        pytest.param(
            {
                "duration": 1,
                "sample_rate": 1_024,
                "nb_files": 1,
                "date_begin": pd.Timestamp("2024-01-01 12:00:00"),
            },
            float,
            complex,
            pytest.raises(
                TypeError,
                match="Cannot convert absolute npz values to complex sx values.",
            ),
            id="float_to_complex_raises_exception",
        ),
    ],
    indirect=["audio_files"],
)
def test_spectrogram_sx_dtype(
    tmp_path: Path,
    audio_files: tuple[list[Path], pytest.fixtures.Subrequest],
    origin_dtype: type[complex],
    target_dtype: type[complex],
    expected_value_dtype: type[complex],
) -> None:
    audio_file, request = audio_files
    af = AudioFile(audio_file[0], strptime_format=TIMESTAMP_FORMAT_TEST_FILES)
    ad = AudioData.from_files([af])
    sft = ShortTimeFFT(hamming(128), 128, 1_024)
    sd = SpectroData.from_audio_data(ad, sft)

    sd.sx_dtype = origin_dtype
    ltas = LTASData.from_spectro_data(sd, 4)
    assert ltas.sx_dtype is float  # Default LTASData behaviour

    assert sd.get_value().dtype == origin_dtype

    sd.write(tmp_path / "npz")

    sf = SpectroFile(
        tmp_path / "npz" / f"{sd}.npz", strptime_format=TIMESTAMP_FORMAT_EXPORTED_FILES
    )

    assert sf.sx_dtype is origin_dtype

    sd2 = SpectroData.from_files([sf])

    assert sd2.sx_dtype is origin_dtype  # Default SpectroData behaviour

    assert ltas.get_value().dtype == float

    sd2.sx_dtype = target_dtype

    if type(expected_value_dtype) is type:
        assert sd2.get_value().dtype == expected_value_dtype
    else:
        with expected_value_dtype as e:
            assert sd2.get_value().dtype == expected_value_dtype

    sd2.sx_dtype = origin_dtype

    assert sd2.get_value().dtype == origin_dtype
