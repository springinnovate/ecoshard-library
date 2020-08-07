Ecoshard
********

The purpose of this library is to simplify the cognitive and logistical data load of Python applications that require specific input data. Ecoshard is an interface that allows access to a central repository of data and a seamless API that allows users to clone specific data while avoiding duplication on the client machine.

The Ecoshard API can also publish data for use in other applications or for use of Ecoshard library specific functionality such as visualization.

Ecoshard is developed in an environment that relies on and generates large GIS data such as rasters. Some functionality in Ecoshard is GIS specific, but in general is useful for all data types.

When used correctly, Ecoshard brings data management to the implementation level, treating data as though they were integrated objects rather than external to the system.

Concepts
========

Structure
---------

  * Library - a remote server which stores/indexes Ecoshards. This library
    is readable/writable through an API key provided by the user. In some
    cases a Library may have a public Catalog that can be read/written
    without an API key. In many cases this Library can provide other
    functionality outside of Ecoshard such as visualization.
  * Catalog - a designation in a Library to help sort individual Ecoshards.
    There can be many Catalogs per Library.
  * Asset ID - a unique identifier in a catalog for an Ecoshard object. It
    is preferable an Asset ID ends with a ``[hash algorithm]_[hash
    value]``.
  * Ecoshard - an Ecoshard is a universally unique string that can identify a piece of data in a single file. The "Eco" comes from the project history for primary use in GIS applications where those data are biophysical data such as landcover rasters. The string is formated as ``[hash algorithm]_[hash value]`` referring to the hashed value of that file with the given "hash algorithm".

Verbs
-----

  * "publish" - upload a file to a library's catalog and record any
    additional metadata associated with that Ecoshard.
  * "fetch" - download a file from a library given a unique Catalog/Asset
    ID pair.
  * "search" - acquire a set of Ecoshard Asset IDs that match a search for
    partial ID, bounding box, and/or description.

Usage
=====

In Code
-------

Start by instantiating a EcoshardLibrary object:

```ecoshard_library = ecoshard.EcoshardLibrary(
  'https://public.ecoshard.org', 'PUT YOUR REAL API KEY HERE', cache_dir)``

The first argument is a URL to the Ecoshard library. This is an online service that must already exist. The second is an API key that is provided to you by the administrator of the Ecoshard library. This argument can be ``None`` in cases where you only want to publish/search/fetch from a public catalog on the library. The ``cache_dir`` points to a writable path where Ecoshard will locally cache any fetched files. This is useful in cases where Ecoshard is used to provide data to many applications. When "fetched" Ecoshard will only download the file if it is not in its cache, download it if so, then hardlink the file to the desired path. This allows Ecoshard to service many similar heavy data needs without duplicating data on the client machine.

Next, fetch an Ecoshard for use in a script:

``ecoshard_library.fetch_by_hash('costa_rica_project', 'md5_23f4876ff19869c81234a76', './landcover_map.tif')``

This command tells the Ecoshard Library object to search the library (specified above as ``https://public.ecoshard.org``) for a file whose hash matches the ``md5`` sum of ``23f4876ff19869c81234a76``. The library object will


Command Line
------------

  * To Ecoshard hash a file:

    ``python -m ecoshard process \[original\_file\] --hashalg md5 --rename``

    (creates an ecoshard from original file with the md5 hash algorithm and
    renames the result rather than creating a new copy)

  * To compress and build overviews of some GeoTIFF files:

    ``python -m ecoshard *.tif --compress --buildoverviews``

    (does a GIS compression of all \*.tif files in the current directory and
    builds overviews for them and renames the result rather than making a new
    copy. Here if --rename had been passed an error would have been raised
    because rasters cannot be in-place compressed. The target output files
    will have the format
    \[original\_filename\]\_compressed\_\[hashalg\]\_\[ecoshard\]\[fileext\])

(does the previous operation but also uploads the results to
gs://ecoshard-root/working-shards and reports the target URLs to stdout)

``python -m ecoshard *.tif ./outputs/*.tif --validate``

(searches the *.tif and ./outputs/*.tif globs for ecoshard files and reports
whether their hashes are valid or not)
