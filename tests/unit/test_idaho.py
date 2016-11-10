'''
Authors: Donnie Marino, Kostas Stamatiou
Contact: dmarino@digitalglobe.com

Unit tests for the gbdxtools.Idaho class
'''

<<<<<<< HEAD
import os.path
import tempfile

import unittest

import shutil

from gbdxtools import Interface
from gbdxtools.idaho import Idaho
import vcr
from auth_mock import get_mock_gbdx_session
=======
from gbdxtools import Interface
from gbdxtools.idaho import Idaho
from auth_mock import get_mock_gbdx_session
import vcr
from os.path import join, isfile, dirname, realpath
import tempfile
import unittest
>>>>>>> upstream-master

# How to use the mock_gbdx_session and vcr to create unit tests:
# 1. Add a new test that is dependent upon actually hitting GBDX APIs.
# 2. Decorate the test with @vcr appropriately
<<<<<<< HEAD
# 3. replace "dummytoken" with a real gbdx token
# 4. Run the tests (existing test shouldn't be affected by use of a real token).  This will record a "cassette".
# 5. replace the real gbdx token with "dummytoken" again
# 6. Edit the cassette to remove any possibly sensitive information (s3 creds for example)

mock_gbdx_session = get_mock_gbdx_session(token="dummytoken")
gbdx = Interface(gbdx_connection=mock_gbdx_session)

# generate the cassette name in a machine nutral way
cassette_name = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cassettes', 'test_get_idaho_chip.yaml')

=======
# 3. Replace "dummytoken" with a real gbdx token
# 4. Run the tests (existing test shouldn't be affected by use of a real token).  This will record a "cassette".
# 5. Replace the real gbdx token with "dummytoken" again
# 6. Edit the cassette to remove any possibly sensitive information (s3 creds for example)

>>>>>>> upstream-master

class IdahoTest(unittest.TestCase):

    _temp_path = None

    @classmethod
    def setUpClass(cls):
<<<<<<< HEAD
        i = Idaho(gbdx)
        assert isinstance(i, Idaho)
        cls._temp_path = tempfile.mkdtemp()
        print("Created: {}".format(cls._temp_path))

    @classmethod
    def tearDownClass(cls):
        print("Deleting: {}".format(cls._temp_path))
        shutil.rmtree(cls._temp_path)

    @vcr.use_cassette(cassette_name)
    def test_get_idaho_chip(self):

        multi_id = '98ce43c5-b4a8-45aa-8597-ae7017ecefb2'
        pan_id = '5e47dfec-4685-476a-94ec-8589e06df349'

        i = Idaho(gbdx)
        i.get_idaho_chip(bucket_name='idaho-images',
                         idaho_id=multi_id,
                         center_lat='48.8611',
                         center_lon='2.3358',
                         pan_id=pan_id,
                         output_folder=self._temp_path,
                         resolution=50)
        assert os.path.isfile(os.path.join(self._temp_path, multi_id+'.tif'))


=======
        mock_gbdx_session = get_mock_gbdx_session(token='dymmytoken')
        cls.gbdx = Interface(gbdx_connection=mock_gbdx_session)
        cls._temp_path = tempfile.mkdtemp()
        print("Created: {}".format(cls._temp_path))

    def test_init(self):
        c = Idaho(self.gbdx)
        self.assertTrue(isinstance(c, Idaho))

    @vcr.use_cassette('tests/unit/cassettes/test_idaho_get_images_by_catid_and_aoi.yaml', filter_headers=['authorization'])
    def test_idaho_get_images_by_catid_and_aoi(self):
        i = Idaho(self.gbdx)
        catid = '10400100203F1300'
        aoi_wkt = "POLYGON ((-105.0207996368408345 39.7338828628182839, -105.0207996368408345 39.7365972921260067, -105.0158751010894775 39.7365972921260067, -105.0158751010894775 39.7338828628182839, -105.0207996368408345 39.7338828628182839))"
        results = i.get_images_by_catid_and_aoi(catid=catid, aoi_wkt=aoi_wkt)
        assert len(results['results']) == 2

    @vcr.use_cassette('tests/unit/cassettes/test_idaho_get_images_by_catid.yaml', filter_headers=['authorization'])
    def test_idaho_get_images_by_catid(self):
        i = Idaho(self.gbdx)
        catid = '10400100203F1300'
        results = i.get_images_by_catid(catid=catid)
        assert len(results['results']) == 12

    @vcr.use_cassette('tests/unit/cassettes/test_idaho_describe_images.yaml', filter_headers=['authorization'])
    def test_idaho_describe_images(self):
        i = Idaho(self.gbdx)
        catid = '10400100203F1300'
        description = i.describe_images(i.get_images_by_catid(catid=catid))
        assert description['10400100203F1300']['parts'][1]['PAN']['id'] =='b1f6448b-aecd-4d9b-99ec-9cad8d079043'
>>>>>>> upstream-master
