# Copyright (C) 2005  Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from typing import Optional

from ._util import loadfile


class PaddingInfo(object):
    """PaddingInfo()

    Abstract padding information object.

    This will be passed to the callback function that can be used
    for saving tags.

    ::

        def my_callback(info: PaddingInfo):
            return info.get_default_padding()

    The callback should return the amount of padding to use (>= 0) based on
    the content size and the padding of the file after saving. The actual used
    amount of padding might vary depending on the file format (due to
    alignment etc.)

    The default implementation can be accessed using the
    :meth:`get_default_padding` method in the callback.

    Attributes:
        size_diff (`int`): The amount metadata added or removed compared to the
            original. Negative in case new metadata is smaller.
        new_tail_size (`int`): The amount of data following the padding
        new_head_size (`int | None`): The amount of bytes preceding the padding
        fs_block_size (`int | None`): The filesystem block size
    """

    # TODO?: cleanup args if changing the function signature is ok
    def __init__(self, padding: int, new_tail_size: int,
                 new_head_size: Optional[int] = None,
                 fs_block_size: Optional[int] = None):
        self.size_diff = -padding
        self.new_tail_size = new_tail_size
        self.new_head_size = new_head_size
        self.fs_block_size = fs_block_size

        # Back-compat
        self.padding = -self.size_diff
        self.size = self.new_tail_size

    def get_default_padding(self) -> int:
        """The default implementation is currently equivalent to the "sharing"
        algorithm.
        The algorithm and return value can change between versions.

        Returns:
            int: Amount of padding after saving
        """

        # TODO?: default to storage when self.fs_block_size is not None
        return self.get_padding_for_sharing()

    def get_padding_for_sharing(self) -> int:
        """Tries to select an amount that is big enough to make future edits,
        while staying reasonably small.
        The return value can change between versions.

        Returns:
            int: Amount of padding after saving
        """
        high = 1024 * 10 + self.size // 100  # 10 KiB + 1% of trailing data
        low = 1024 + self.size // 1000  # 1 KiB + 0.1% of trailing data

        if self.padding >= 0:
            # enough padding left
            if self.padding > high:
                # padding too large, reduce
                return low
            # just use existing padding as is
            return self.padding
        else:
            # not enough padding, add some
            return low

    def get_padding_for_storage(self) -> int:
        """Selects an amount that causes the least filesystem block changes.
        The return value can change between versions.

        The point of this strategy is to avoid rewriting more data than needed.
        This improves performance by reducing the amout we actually copy,
        which also greatly improves storage use for copy-on-write filesystems.

        Returns:
            int: Amount of padding after saving
        """
        if self.new_head_size is None:
            raise ValueError("get_padding_for_storage requires new_head_size")

        if self.fs_block_size is None:
            raise ValueError("get_padding_for_storage requries fs_block_size")

        old_head_size = self.new_head_size - self.size_diff
        old_align = old_head_size % self.fs_block_size

        # Ensure metadata + padding is block aligned
        res = self.fs_block_size - (self.new_head_size % self.fs_block_size)

        # Ensure old offset in the following block is preserved
        # This is makes all following blocks stay the same
        res += old_align

        # Don't exceed a single block (can happen when new_head_size <= old_align)
        return res % self.fs_block_size

    def _get_padding(self, user_func):
        if user_func is None:
            return self.get_default_padding()
        else:
            return user_func(self)

    def __repr__(self):
        return "<%s size=%d padding=%d>" % (
            type(self).__name__, self.size, self.padding)


class Tags(object):
    """`Tags` is the base class for many of the tag objects in Mutagen.

    In many cases it has a dict like interface.
    """

    __module__ = "mutagen"

    def pprint(self):
        """
        Returns:
            text: tag information
        """

        raise NotImplementedError


class Metadata(Tags):
    """Metadata(filething=None, **kwargs)

    Args:
        filething (filething): a filename or a file-like object or `None`
            to create an empty instance (like ``ID3()``)

    Like :class:`Tags` but for standalone tagging formats that are not
    solely managed by a container format.

    Provides methods to load, save and delete tags.
    """

    __module__ = "mutagen"

    def __init__(self, *args, **kwargs):
        if args or kwargs:
            self.load(*args, **kwargs)

    @loadfile()
    def load(self, filething, **kwargs):
        raise NotImplementedError

    @loadfile(writable=False)
    def save(self, filething=None, **kwargs):
        """save(filething=None, **kwargs)

        Save changes to a file.

        Args:
            filething (filething): or `None`
        Raises:
            MutagenError: if saving wasn't possible
        """

        raise NotImplementedError

    @loadfile(writable=False)
    def delete(self, filething=None):
        """delete(filething=None)

        Remove tags from a file.

        In most cases this means any traces of the tag will be removed
        from the file.

        Args:
            filething (filething): or `None`
        Raises:
            MutagenError: if deleting wasn't possible
        """

        raise NotImplementedError
