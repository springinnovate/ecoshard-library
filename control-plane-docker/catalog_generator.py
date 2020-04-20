"""Generate a STAC catalog."""
import os
import subprocess

import datetime
import pystac

WORKING_DIR = 'catalog_generator_workspace'


def main():
    """Entry point."""
    try:
        os.makedirs(WORKING_DIR)
    except OSError:
        pass

    output = subprocess.check_output(
        'gsutil ls gs://salo-api/test_rasters', shell=True)
    file_list = [x.rstrip() for x in output.decode('utf-8').split('\n') if x]
    item_list = []

    catalog = pystac.Catalog(
        id='salo',
        description='salo api',
        href='gs://salo-api/test_rasters')

    for gs_uri in file_list:
        base_id = os.path.basename(os.path.splitext(gs_uri)[0])
        item = pystac.Item(
            id=base_id,
            geometry=None,
            bbox=None,
            datetime=datetime.datetime.utcnow(),
            properties={}
            )
        item.add_asset(
            key=base_id,
            asset=pystac.Asset(
                href=gs_uri,
                media_type=pystac.MediaType.GEOTIFF))
        catalog.add_item(item)

        print(gs_uri)

    catalog.normalize_hrefs('salo')
    catalog.save('SELF_CONTAINED')


if __name__ == '__main__':
    main()
