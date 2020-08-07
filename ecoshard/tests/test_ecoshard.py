"""Ecoshard test suite."""
import os
import tempfile
import shutil
import unittest

import ecoshard
import numpy
from osgeo import gdal
from osgeo import osr


def _build_test_raster(raster_path):
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)

    gtiff_driver = gdal.GetDriverByName('GTiff')
    n = 100
    new_raster = gtiff_driver.Create(
        raster_path, n, n, 1, gdal.GDT_Int32, options=[
            'TILED=YES', 'BIGTIFF=YES', 'COMPRESS=NONE',
            'BLOCKXSIZE=16', 'BLOCKYSIZE=16'])
    new_raster.SetProjection(srs.ExportToWkt())
    new_raster.SetGeoTransform([100.0, 1.0, 0.0, 100.0, 0.0, -1.0])
    new_band = new_raster.GetRasterBand(1)
    new_band.SetNoDataValue(-1)
    array = numpy.array(range(n*n), dtype=numpy.int32).reshape((n, n))
    new_band.WriteArray(array)
    new_raster.FlushCache()
    new_band = None
    new_raster = None


class EcoShardTests(unittest.TestCase):
    """Tests for the PyGeoprocesing 1.0 refactor."""

    def setUp(self):
        """Create a temporary workspace that's deleted later."""
        self.workspace_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up remaining files."""
        shutil.rmtree(self.workspace_dir)

    def test_hash_file(self):
        """Test ecoshard.hash_file."""
        working_dir = self.workspace_dir
        base_path = os.path.join(working_dir, 'test_file.txt')
        target_token_path = '%s.COMPLETE' % base_path

        with open(base_path, 'w') as base_file:
            base_file.write('test')

        # make a different target dir so it gets copied
        target_dir = os.path.join(working_dir, 'output')
        ecoshard.hash_file(
            base_path, target_token_path=target_token_path,
            target_dir=target_dir, rename=False,
            hash_algorithm='md5', force=False)

        expected_file_path = os.path.join(
            target_dir, 'test_file_md5_098f6bcd4621d373cade4e832627b4f6.txt')
        self.assertTrue(os.path.exists(expected_file_path))
        self.assertTrue(os.path.exists(target_token_path))

    def test_hash_file_rename(self):
        """Test ecoshard.hash_file with a rename."""
        working_dir = self.workspace_dir
        base_path = os.path.join(working_dir, 'test_file.txt')
        target_token_path = '%s.COMPLETE' % base_path

        with open(base_path, 'w') as base_file:
            base_file.write('test')

        ecoshard.hash_file(
            base_path, target_token_path=target_token_path,
            target_dir=None, rename=True,
            hash_algorithm='md5', force=False)

        expected_file_path = os.path.join(
            working_dir, 'test_file_md5_098f6bcd4621d373cade4e832627b4f6.txt')
        self.assertTrue(os.path.exists(expected_file_path))
        # indicates the file has been renamed
        self.assertFalse(os.path.exists(base_path))

    def test_force(self):
        """Test ecoshard.hash_file with a force rename."""
        working_dir = self.workspace_dir
        base_path = os.path.join(
            working_dir, 'test_file_sha224_fffffffffff.txt')
        target_token_path = '%s.COMPLETE' % base_path

        with open(base_path, 'w') as base_file:
            base_file.write('test')

        ecoshard.hash_file(
            base_path, target_token_path=target_token_path,
            target_dir=None, rename=True,
            hash_algorithm='md5', force=True)

        expected_file_path = os.path.join(
            working_dir, 'test_file_md5_098f6bcd4621d373cade4e832627b4f6.txt')
        self.assertTrue(os.path.exists(expected_file_path))
        # indicates the file has been renamed
        self.assertFalse(os.path.exists(base_path))

    def test_exceptions_in_hash(self):
        """Test ecoshard.hash_file raises exceptions in bad cases."""
        working_dir = self.workspace_dir
        base_path = os.path.join(working_dir, 'test_file.txt')
        target_token_path = '%s.COMPLETE' % base_path

        with open(base_path, 'w') as base_file:
            base_file.write('test')

        # test that target dir defined and rename True raises an exception
        with self.assertRaises(ValueError) as cm:
            ecoshard.hash_file(
                base_path, target_token_path=target_token_path,
                target_dir='output', rename=True,
                hash_algorithm='md5', force=False)
        self.assertTrue('but rename is True' in str(cm.exception))

        # test that a base path already in ecoshard format raises an exception
        base_path = os.path.join(
            working_dir, 'test_file_sha224_fffffffffff.txt')
        with self.assertRaises(ValueError) as cm:
            ecoshard.hash_file(
                base_path, target_token_path=target_token_path,
                target_dir=None, rename=True,
                hash_algorithm='md5', force=False)
        self.assertTrue('already be an ecoshard' in str(cm.exception))

    def test_validate_hash(self):
        """Test ecoshard.validate_hash."""
        working_dir = self.workspace_dir
        # we know the hash a priori, just make the file
        base_path = os.path.join(
            working_dir, 'test_file_md5_098f6bcd4621d373cade4e832627b4f6.txt')
        with open(base_path, 'w') as base_file:
            base_file.write('test')
        self.assertTrue(ecoshard.validate(base_path))

        # test that files that are not in ecoshard format raise an exception
        with self.assertRaises(ValueError) as cm:
            not_an_ecoshard_path = 'test.txt'
            ecoshard.validate(not_an_ecoshard_path)
        self.assertTrue('does not match an ecoshard' in str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            new_file_path = os.path.join(
                working_dir,
                'test_file_md5_098f6bcd4621d373cade4e832627b4f5.txt')
            shutil.copyfile(base_path, new_file_path)
            ecoshard.validate(new_file_path)
        self.assertTrue('hash does not match' in str(cm.exception))

    def test_build_overviews(self):
        """Test ecoshard.build_overviews."""
        raster_path = os.path.join(self.workspace_dir, 'test_raster.tif')
        _build_test_raster(raster_path)

        target_token_path = '%s.COMPLETE' % raster_path
        ecoshard.build_overviews(
            raster_path, target_token_path=target_token_path,
            interpolation_method='near')
        raster = gdal.OpenEx(raster_path, gdal.OF_RASTER)
        band = raster.GetRasterBand(1)
        overview_count = band.GetOverviewCount()
        band = None
        raster = None
        self.assertEqual(overview_count, 6)

    def test_compress_raster(self):
        """Test ecoshard.compress_raster."""
        raster_path = os.path.join(self.workspace_dir, 'test_raster.tif')
        _build_test_raster(raster_path)
        compressed_raster_path = os.path.join(
            self.workspace_dir, 'test_raster_compressed.tif')

        ecoshard.compress_raster(
            raster_path, compressed_raster_path, compression_algorithm='LZW',
            compression_predictor=2)

        # if its compressed, it should be smaller!
        self.assertTrue(
            os.path.getsize(compressed_raster_path) <
            os.path.getsize(raster_path))
