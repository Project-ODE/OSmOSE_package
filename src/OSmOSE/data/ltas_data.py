"""LTASData is a special form of SpectroData.

The Sx values from a LTASData object are computed recursively.
LTAS should be preferred to classic spectrograms in cases where the audio is really long.
In that case, the corresponding number of time bins (scipy.ShortTimeFTT.p_nums) is
too long for the whole Sx matrix to be computed once.

The LTAS are rather computed recursively. If the number of temporal bins is higher than
a target p_num value, the audio is split in p_num parts. A separate sft is computed
on each of these bits and averaged so that the end Sx presents p_num temporal windows.

This averaging is performed recursively: if the audio data is such that after a first split,
the p_nums for each part still is higher than p_num, the parts are further split and
each part is replaced with an average of the stft performed within it.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy.signal import ShortTimeFFT
from tqdm import tqdm

from OSmOSE.data.spectro_data import SpectroData
from OSmOSE.data.spectro_item import SpectroItem

if TYPE_CHECKING:

    from pandas import Timestamp

    from OSmOSE.data.audio_data import AudioData


class LTASData(SpectroData):
    """LTASData is a special form of SpectroData.

    The Sx values from a LTASData object are computed recursively.
    LTAS should be preferred to classic spectrograms in cases where the audio is really long.
    In that case, the corresponding number of time bins (scipy.ShortTimeFTT.p_nums) is
    too long for the whole Sx matrix to be computed once.

    The LTAS are rather computed recursively. If the number of temporal bins is higher than
    a target p_num value, the audio is split in p_num parts. A separate sft is computed
    on each of these bits and averaged so that the end Sx presents p_num temporal windows.

    This averaging is performed recursively: if the audio data is such that after a first split,
    the p_nums for each part still is higher than p_num, the parts are further split and
    each part is replaced with an average of the stft performed within it.

    """

    def __init__(
        self,
        items: list[SpectroItem] | None = None,
        audio_data: AudioData = None,
        begin: Timestamp | None = None,
        end: Timestamp | None = None,
        fft: ShortTimeFFT | None = None,
        nb_time_bins: int = 1920,
    ) -> None:
        """Initialize a SpectroData from a list of SpectroItems.

        Parameters
        ----------
        items: list[SpectroItem]
            List of the SpectroItem constituting the SpectroData.
        audio_data: AudioData
            The audio data from which to compute the spectrogram.
        begin: Timestamp | None
            Only effective if items is None.
            Set the begin of the empty data.
        end: Timestamp | None
            Only effective if items is None.
            Set the end of the empty data.
        fft: ShortTimeFFT
            The short time FFT used for computing the spectrogram.

        """
        ltas_fft = LTASData.get_ltas_fft(fft)
        super().__init__(
            items=items, audio_data=audio_data, begin=begin, end=end, fft=ltas_fft
        )
        self.nb_time_bins = nb_time_bins

    def get_value(self, depth: int = 0) -> np.ndarray:
        if self.shape[1] <= self.nb_time_bins:
            return super().get_value()
        sub_spectros = [
            LTASData.from_spectro_data(
                SpectroData.from_audio_data(ad, self.fft),
                nb_time_bins=self.nb_time_bins,
            )
            for ad in self.audio_data.split(self.nb_time_bins)
        ]

        if depth == 0:
            m = []
            for sub_spectro in tqdm(sub_spectros):
                m.append(
                    np.mean(sub_spectro.get_value(depth + 1), axis=1),
                )
            return np.vstack(m).T

        return np.vstack(
            [
                np.mean(sub_spectro.get_value(depth + 1), axis=1)
                for sub_spectro in sub_spectros
            ],
        ).T

    @classmethod
    def from_spectro_data(cls, spectro_data: SpectroData, nb_time_bins: int):
        items = spectro_data.items
        audio_data = spectro_data.audio_data
        begin = spectro_data.begin
        end = spectro_data.end
        fft = spectro_data.fft
        return cls(
            items=items,
            audio_data=audio_data,
            begin=begin,
            end=end,
            fft=fft,
            nb_time_bins=nb_time_bins,
        )

    @staticmethod
    def get_ltas_fft(fft: ShortTimeFFT):
        win = fft.win
        fs = fft.fs
        mfft = fft.mfft
        hop = win.shape[0]
        return ShortTimeFFT(win=win, hop=hop, fs=fs, mfft=mfft)
