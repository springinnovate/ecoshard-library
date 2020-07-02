STAC/Geoserver Platform
=======================

Architecture
------------

    * Disk resize service listens on port 8082

Secrets
-------

In order to allow for automatic disk resizing, a GCE drive must be mounted on the host where the device is formatted as ext4. If this is the case then you can define the following variables in the ``stac_envs`` file:

    * ``DISK_RESIZE_SERVICE_ZONE`` -- GCE service zone for the disk
    * ``DISK_RESIZE_SERVICE_DISK_NAME`` -- the name of the disk in the GCE console/context.
    * ``DISK_RESIZE_SERVICE_MAX_SIZE_GB`` -- max allowed size of the disk in GB
    * ``DISK_RESIZE_SERVICE_DEVICE_NAME`` -- the name of the device as is it mounted locally to the host (i.e. ``/dev/sdb``)
    * ``DISK_RESIZE_SERVICE_ACCOUNT_KEYFILE`` -- a path to a GCE ``.json`` keyfile that has the following permissions enabled for the given disk:
        * ``compute.disks.create`` on the project to be able to create a new disk
        * ``compute.instances.attachDisk`` on the VM instance
        * ``compute.disks.use`` permission on the disk to attach
