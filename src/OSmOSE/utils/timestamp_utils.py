"""Utils for working with timestamps."""

import os
import re
from datetime import datetime, timedelta
from typing import Iterable, List

import pandas as pd
from pandas import Timestamp

from OSmOSE.config import TIMESTAMP_FORMAT_AUDIO_FILE

_REGEX_BUILDER = {
    "%Y": r"([12]\d{3})",
    "%y": r"(\d{2})",
    "%m": r"(0[1-9]|1[0-2])",
    "%d": r"([0-2]\d|3[0-1])",
    "%H": r"([0-1]\d|2[0-4])",
    "%I": r"(0[1-9]|1[0-2])",
    "%p": r"(AM|PM)",
    "%M": r"([0-5]\d)",
    "%S": r"([0-5]\d)",
    "%f": r"(\d{1,6})",
    "%Z": r"((?:\w+)(?:[-/]\w+)*(?:[\+-]\d+)?)",
    "%z": r"([\+-]\d{2}:?\d{2})",
}


def check_epoch(df):
    """Add epoch column to dataframe."""
    if "epoch" in df.columns:
        return df
    try:
        df["epoch"] = df.timestamp.apply(
            lambda x: datetime.strptime(x[:26], "%Y-%m-%dT%H:%M:%S.%f").timestamp(),
        )
        return df
    except ValueError:
        print(
            "Please check that you have either a timestamp column (format ISO 8601 Micro s) or an epoch column",
        )
        return df


def substract_timestamps(
    input_timestamp: pd.DataFrame,
    files: List[str],
    index: int,
) -> timedelta:
    """Substracts two timestamp_list from the "timestamp" column of a dataframe at the indexes of files[i] and files[i-1] and returns the time delta between them

    Parameters
    ----------
        input_timestamp: the pandas DataFrame containing at least two columns: filename and timestamp

        files: the list of file names corresponding to the filename column of the dataframe

        index: the index of the file whose timestamp will be substracted

    Returns
    -------
        The time between the two timestamp_list as a datetime.timedelta object

    """
    if index == 0:
        return timedelta(seconds=0)

    cur_timestamp: str = input_timestamp[input_timestamp["filename"] == files[index]][
        "timestamp"
    ].values[0]
    cur_timestamp: datetime = to_timestamp(cur_timestamp)
    next_timestamp: str = input_timestamp[
        input_timestamp["filename"] == files[index + 1]
    ]["timestamp"].values[0]
    next_timestamp: datetime = to_timestamp(next_timestamp)

    return next_timestamp - cur_timestamp


def to_timestamp(string: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(string)
    except ValueError:
        raise ValueError(
            f"The timestamp '{string}' must match format %Y-%m-%dT%H:%M:%S%z.",
        )


def strftime_osmose_format(date: pd.Timestamp) -> str:
    """Format a Timestamp to the OSmOSE format.

    Parameters
    ----------
    date: pandas.Timestamp
        The Timestamp to format.
        If the Timestamp is timezone-naive, it will be localized to UTC.

    Returns
    -------
    str:
        The Timestamp in OSmOSE's %Y-%m-%dT%H:%M:%S.%f%z format.
        %f is limited to a millisecond precision.

    Examples
    --------
    >>> strftime_osmose_format(Timestamp('2024-10-17 10:14:11.933634', tz="US/Eastern"))
    '2024-10-17T10:14:11.933-0400'

    """
    if date.tz is None:
        date = date.tz_localize("UTC")

    str_time = date.strftime(TIMESTAMP_FORMAT_AUDIO_FILE)
    return (
        str_time[:-8] + str_time[-5:]
    )  # Changes microsecond precision to millisecond precision


def build_regex_from_datetime_template(datetime_template: str) -> str:
    r"""Build the regular expression for parsing Timestamps based on a template string.

    Parameters
    ----------
    datetime_template: str
        A datetime template string using strftime codes.

    Returns
    -------
    str:
        A regex that can be used to parse a Timestamp from a string.
        The timestamp in the string must be written in the specified template

    Examples
    --------
    >>> build_regex_from_datetime_template('year_%Y_hour_%H')
    'year_([12]\\d{3})_hour_([0-1]\\d|2[0-4])'

    """
    escaped_characters = "()"
    for escaped in escaped_characters:
        datetime_template = datetime_template.replace(escaped, f"\\{escaped}")
    for key, value in _REGEX_BUILDER.items():
        datetime_template = datetime_template.replace(key, value)
    return datetime_template


def is_datetime_template_valid(datetime_template: str) -> bool:
    """Check the validity of a datetime template string.

    Parameters
    ----------
    datetime_template: str
        The datetime template following which timestamps are written.
        It should use valid strftime codes (see https://strftime.org/).

    Returns
    -------
    bool:
    True if datetime_template only uses supported strftime codes, False otherwise.

    Examples
    --------
    >>> is_datetime_template_valid('year_%Y_hour_%H')
    True
    >>> is_datetime_template_valid('unsupported_code_%u_hour_%H')
    False

    """
    strftime_identifiers = [key.lstrip("%") for key in _REGEX_BUILDER]
    percent_sign_indexes = (
        index for index, char in enumerate(datetime_template) if char == "%"
    )
    for index in percent_sign_indexes:
        if index == len(datetime_template) - 1:
            return False
        if datetime_template[index + 1] not in strftime_identifiers:
            return False
    return True


def strptime_from_text(text: str, datetime_template: str) -> Timestamp:
    """Extract a Timestamp written in a string with a specified format.

    Parameters
    ----------
    text: str
        The text in which the timestamp should be extracted, ex '2016_06_13_14:12.txt'.
    datetime_template: str
         The datetime template used in the text.
         It should use valid strftime codes (https://strftime.org/).
         Example: '%y%m%d_%H:%M:%S'.

    Returns
    -------
    pandas.Timestamp:
        The timestamp extracted from the text according to datetime_template

    Examples
    --------
    >>> strptime_from_text('2016_06_13_14:12.txt', '%Y_%m_%d_%H:%M')
    Timestamp('2016-06-13 14:12:00')
    >>> strptime_from_text('D_12_03_21_hour_11:45:10_PM', '%y_%m_%d_hour_%I:%M:%S_%p')
    Timestamp('2012-03-21 23:45:10')

    """
    if not is_datetime_template_valid(datetime_template):
        msg = f"{datetime_template} is not a supported strftime template"
        raise ValueError(msg)

    regex_pattern = build_regex_from_datetime_template(datetime_template)
    regex_result = re.findall(regex_pattern, text)

    if not regex_result:
        msg = f"{text} did not match the given {datetime_template} template"
        raise ValueError(msg)

    date_string = "_".join(regex_result[0])
    cleaned_date_template = "_".join(
        c + datetime_template[i + 1]
        for i, c in enumerate(datetime_template)
        if c == "%"
    )
    return pd.to_datetime(date_string, format=cleaned_date_template)


def associate_timestamps(
    audio_files: Iterable[str],
    datetime_template: str,
) -> pd.Series:
    """Return a pandas series with timestamps assignated to the audio files.

    Parameters
    ----------
    audio_files: Iterable[str]
        Files from which the timestamps should be extracted.
        They must share a same datetime format.
    datetime_template: str
        The datetime template used in filename.
        It should use valid strftime codes (https://strftime.org/).
        Example: '%y%m%d_%H:%M:%S'

    Returns
    -------
    pandas.Series:
        A series with audio files name indexes and timestamp values.

    """
    files_with_timestamps = {
        file: strptime_from_text(file, datetime_template) for file in audio_files
    }
    series = pd.Series(data=files_with_timestamps, name="timestamp")
    series.index.name = "filename"
    return series.sort_values().reset_index()


def get_timestamps(
    path_osmose_dataset: str,
    campaign_name: str,
    dataset_name: str,
    resolution: str,
) -> pd.DataFrame:
    """Read infos from APLOSE timestamp csv file

    Parameters
    ----------
        path_osmose_dataset: 'str'
            usually '/home/datawork-osmose/dataset/'

        campaign_name: 'str'
            Name of the campaign
        dataset_name: 'str'
            Name of the dataset
        resolution: 'str'
            Resolution of the dataset

    Returns
    -------
        df: pd.DataFrame
            The timestamp file is read and returned as a DataFrame

    """
    csv = os.path.join(
        path_osmose_dataset,
        campaign_name,
        dataset_name,
        "data",
        "audio",
        resolution,
        "timestamp.csv",
    )

    if os.path.exists(csv):
        df = pd.read_csv(csv, parse_dates=["timestamp"])
        return df
    raise ValueError(f"{csv} does not exist")
