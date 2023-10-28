"""
Alternating text and code
=========================

Sphinx-Gallery is capable of transforming Python files into reST files
with a notebook structure. For this to be used you need to respect some syntax
rules. This example demonstrates how to alternate text and code blocks and some
edge cases. It was designed to be compared with the
:download:`source Python script <plot_parse.py>`."""


# %%
# This is the first text block and directly follows the header docstring above.

import numpy as np  # noqa: F401

# %%

# You can separate code blocks using either a single line of ``#``'s
# (>=20 columns), ``#%%``, or ``# %%``. For consistency, it is recommend that
# you use only one of the above three 'block splitter' options in your project.
A = 1

import matplotlib.pyplot as plt  # noqa: F401

# %%
# Block splitters allow you alternate between code and text blocks **and**
# separate sequential blocks of code (above) and text (below).

##############################################################################
# A line of ``#``'s also works for separating blocks. The above line of ``#``'s
# separates the text block above from this text block. Notice however, that
# separated text blocks only shows as a new lines between text, in the rendered
# output.


def dummy():
    """This should not be part of a 'text' block'"""  # noqa: D404

    # %%
    # This comment inside a code block will remain in the code block
    pass


# this line should not be part of a 'text' block

# %%
#
# ####################################################################
#
# The above syntax makes a line cut in Sphinx. Note the space between the first
# ``#`` and the line of ``#``'s.

# %%
# .. warning::
#     The next kind of comments are not supported (notice the line of ``#``'s
#     and the ``# %%`` start at the margin instead of being indented like
#     above) and become too hard to escape so just don't use code like this::
#
#         def dummy2():
#             """Function docstring"""
#         ####################################
#         # This comment
#         # %%
#         # and this comment inside python indentation
#         # breaks the block structure and is not
#         # supported
#             dummy2
#

"""Free strings are not supported. They will be rendered as a code block"""

# %%
# New lines can be included in your text block and the parser
# is capable of retaining this important whitespace to work with Sphinx.
# Everything after a block splitter and starting with ``#`` then one space,
# is interpreted by Sphinx-Gallery to be a reST text block. Keep your text
# block together using ``#`` and a space at the beginning of each line.
#
# reST header within text block
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# %%
# Raw data preparation
# ------------------------
# Before you can build your dataset: 
# Step 1 
# ^^^^^^^^^
# choose a dataset name (should not contain any special character, including '-'⁾ ; 
# Step 2
# ^^^^^^^^^
# create the folder ``/home/datawork-osmose/dataset/{dataset_name}`` (or ``home/datawork-osmose/dataset/{campaign_name}/{dataset_name}`` in case of a recording campaign); 
# * place in this folder your audio data, they can be individual files or contain within multiple sub-folders ; 
# * if you have any csv files (either a ``timestamp.csv`` or ``*gps*.csv`` file) should also be placed in this folder ;

# %% 
# **Important remarks:** 
# - about timestamps : all timestamps from your original data (from your audio filenames or from your csv files) MUST follow the same timestamp template which should be given in ``date_template`` ; 
# - about ``*gps*.csv`` file : this file provides the GPS track (ie latitude and longitude coordinates) of a moving hydrophone. This file must contain the term *gps* in its filename ; 
# - about auxiliary csv files : they must contain headers with the following standardized names : timestamp , depth , lat , lon




print("one")

# %%
#

# another way to separate code blocks shown above
B = 1

# %%
# Code blocks containing Jupyter magic are executable
#     .. code-block:: bash
#
#       %%bash
#       # This could be run!
#

# %%
# Last text block.
#
# That's all folks !
#
# .. literalinclude:: plot_parse.py
#
#
