STAC/Geoserver Platform
=======================

Services
--------

    * ``stac_manager`` (port 8888), primary STAC service with functions to ``publish``, ``fetch``, ``delete``, STAC assets. Includes ``/list`` search console and ``/view`` layer previewer.

    * ``geoserver`` (port 8080), serves WMS tiles and used by STAC manager to register new assets

    * ``nginx`` (port 80, 443), two configurations:
        * stac_api_nginx_conf.d
            * reverse proxy to map ``https://../api`` to ``stac_manager:8888/api`` and ``https://../geoserver`` to ``geoserver:8080/geoserver``
        * geoserver_node_conf.d
            * maps ``http://../geoserver`` to ``geoserver:8080/geoserver`` service


    * ``db`` (port 5432), PostgreSQL database. Used by ``stac_manager`` for authentication and STAC catalog storage.

    * ``expand_drive_service`` (port 8082), used to inrease the size of the disk used by the Geoserver node.
         * ``/resize``, ``POST``, ``{'gb_to_add': '12'}``

Configuration
-------------

When deploying the platform you must create a file call ``stac_envs``. This file sets environment variables for the Docker containers that allow them to operate correctly. An example file is given in the root of this project at ``example_stac_envs``.

    * ``DISK_RESIZE_SERVICE_ZONE`` -- GCE service zone for the disk
    * ``DISK_RESIZE_SERVICE_DISK_NAME`` -- the name of the disk in the GCE console/context.
    * ``DISK_RESIZE_SERVICE_MAX_SIZE_GB`` -- max allowed size of the disk in GB
    * ``DISK_RESIZE_SERVICE_DEVICE_NAME`` -- the name of the device as is it mounted locally to the host (i.e. ``/dev/sdb``)
    * ``DISK_RESIZE_SERVICE_ACCOUNT_KEYFILE`` -- a path to a GCE ``.json`` keyfile that has the following permissions enabled for the given disk:
        * ``compute.disks.create`` on the project to be able to create a new disk
        * ``compute.instances.attachDisk`` on the VM instance
        * ``compute.disks.use`` permission on the disk to attach

