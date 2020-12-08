Release History
===============

0.4.1 (2020/12/07)
------------------
* Fixed issue with "``hash_val`` is not defined".

0.4.0 (2019/04/13)
------------------
* Changed behavior of command line function, now takes one of two primary
  commands ``process`` or ``publish``. The command ``process`` behaves like
  the original command line utility with same arguments and behavior. The
  ``publish`` command takes a Google Bucket URI, host to an ecoshard server,
  and an api key and published the raster to that server.
* Fixed an issue when summing up that would ignore nodata values.
* Fixes an issue where the overview interpolation argument was ignored.
* Added a ``download_and_unzip`` function to the API.

0.3.3 (2019/11/09)
------------------
* Fixed an issue that would cause the download rate to be under estimated.

0.3.1 (2019/10/07)
------------------
* Fixing an issue in download_to_url where the file might not be flushed and the
  final log message is not printed.

0.3.0 (2019/09/26)
------------------
* Added a new command line mode –reduce_factor that reduces the number of pixels
  in a raster by that integer amount. Ex:

    ``python -m ecoshard base.tif --reduce_factor 4 max target.tif``

    this call makes the size of the pixels in base.tif 4 times larger on the
    edge, thus reducing the total size of the image by 16 times, the convolution
    upsample is done with a "max" and the output file is ``target.tif``. The
    modes "min", "max", "sum", "average", "mode" are available.

0.2.2 (2019/09/24)
------------------
* Added a ``download_url`` function to ``ecoshard`` to fetch files via
  http(s).
* Developing Flask module to visualize ecoshards.

0.2.1 (2019/06/28)
------------------
* Hotfix: gs to gsutil for copying to buckets.

0.2.0 (2019/06/28)
------------------
* Added functionality to download a url.
* Added functionality to copy to a google bucket.
* Fixed an issue on functions that should write a token file but didn't.

0.1.1 (2019/06/27)
------------------
* Added a ``--force`` flag to the command line utility.

0.0.2 (2019/06/26)
------------------
* Initial release.
