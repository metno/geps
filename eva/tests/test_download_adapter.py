import unittest
import logging

import productstatus
import productstatus.api
import productstatus.event

import eva.adapter
import eva.executor
import eva.statsd
import eva.mail


BLANK_UUID = '00000000-0000-0000-0000-000000000000'
RANDOM_UUID = 'f194279e-dfa8-45ff-ab62-1b03d89e9705'


class TestDownloadAdapter(unittest.TestCase):

    def setUp(self):
        self.env = {
            'EVA_DOWNLOAD_DESTINATION': '/path/to/download',
            'EVA_INPUT_DATA_FORMAT': BLANK_UUID,
            'EVA_INPUT_PRODUCT': BLANK_UUID,
            'EVA_INPUT_SERVICE_BACKEND': BLANK_UUID,
        }
        self.group_id = 'group-id'
        self.productstatus_api = productstatus.api.Api('http://localhost:8000')
        self.logger = logging
        self.zookeeper = None
        self.statsd = eva.statsd.StatsDClient()
        self.mailer = eva.mail.NullMailer()
        self.globe = eva.globe.Global(group_id=self.group_id,
                                      logger=self.logger,
                                      mailer=self.mailer,
                                      statsd=self.statsd,
                                      zookeeper=self.zookeeper,
                                      )
        self.executor = eva.executor.NullExecutor(None, self.env, self.globe)

    def create_adapter(self):
        self.adapter = eva.adapter.DownloadAdapter(self.env, self.executor, self.productstatus_api, self.globe)

    def test_productstatus_read_only_default(self):
        """!
        @brief Test that DownloadAdapter doesn't post to Productstatus when
        output configuration is not given.
        """
        self.create_adapter()
        self.assertFalse(self.adapter.post_to_productstatus())

    def test_productstatus_write_with_output_config(self):
        """!
        @brief Test that DownloadAdapter posts to Productstatus when valid
        output configuration is given.
        """
        self.env.update({
            'EVA_OUTPUT_BASE_URL': 'file:///path/to/download',
            'EVA_OUTPUT_LIFETIME': '60',
            'EVA_OUTPUT_SERVICE_BACKEND': RANDOM_UUID,
            'EVA_PRODUCTSTATUS_API_KEY': '5bcf851f09bc65043d987910e1448781fcf4ea12',
            'EVA_PRODUCTSTATUS_USERNAME': 'admin',
        })
        self.create_adapter()
        self.assertTrue(self.adapter.post_to_productstatus)

    def test_input_output_service_backend_equal(self):
        """!
        @brief Test that the input service backend cannot be the same as the
        output service backend.
        """
        self.env.update({
            'EVA_OUTPUT_BASE_URL': 'file:///path/to/download',
            'EVA_OUTPUT_LIFETIME': 60,
            'EVA_OUTPUT_SERVICE_BACKEND': BLANK_UUID,
            'EVA_PRODUCTSTATUS_API_KEY': '5bcf851f09bc65043d987910e1448781fcf4ea12',
            'EVA_PRODUCTSTATUS_USERNAME': 'admin',
        })
        with self.assertRaises(eva.exceptions.InvalidConfigurationException):
            self.create_adapter()

    def test_parse_bytes_sec_from_lines(self):
        """!
        @brief Test that wget speeds can be parsed.
        """
        self.create_adapter()
        self.assertEqual(
            self.adapter.parse_bytes_sec_from_lines(
                ['foo\r100  285M  100  285M    0     0   562M      0 --:--:-- --:--:-- --:--:--  562M    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0']
            ),
            589299712
        )
        self.assertEqual(
            self.adapter.parse_bytes_sec_from_lines(
                ['100  285M  100  22K    0     0   22K      0 --:--:-- --:--:-- --:--:--  22K    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0']
            ),
            22528
        )
