"""Generate a STAC catalog."""
import pystac


def main():
    """Entry point."""
    catalog = pystac.Catalog(id='salo', description='salo api')
    catalog.normalize_and_save('salo', catalog_type='SELF_CONTAINED')


if __name__ == '__main__':
    main()
