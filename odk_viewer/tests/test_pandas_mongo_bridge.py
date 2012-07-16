import os
from odk_logger.models.xform import XForm
from main.tests.test_base import MainTestCase
from odk_viewer.pandas_mongo_bridge import *

class TestPandasMongoBridge(MainTestCase):
    def setUp(self):
        self._create_user_and_login()

    def _publish_single_level_repeat_form(self):
        xls_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../fixtures/new_repeats/new_repeats.xls"
        )
        count = XForm.objects.count()
        response = self._publish_xls_file(xls_file_path)
        self.assertEqual(XForm.objects.count(), count + 1)
        self.xform = XForm.objects.all().reverse()[0]
        self.survey_name = u"new_repeats"

    def _submit_single_level_repeat_instance(self):
        xml_submission_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../fixtures/new_repeats/instances/new_repeats_2012-07-05-14-33-53.xml"
        )
        self._make_submission(xml_submission_file_path)
        self.assertEqual(self.response.status_code, 201)

    def _publish_nested_repeats_form(self):
        xls_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../fixtures/nested_repeats/nested_repeats.xls"
        )
        count = XForm.objects.count()
        response = self._publish_xls_file(xls_file_path)
        self.assertEqual(XForm.objects.count(), count + 1)
        self.xform = XForm.objects.all().reverse()[0]
        self.survey_name = u"nested_repeats"

    def _submit_nested_repeats_instance(self):
        xml_submission_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "../fixtures/nested_repeats/instances/nested_repeats_01.xml"
        )
        self._make_submission(xml_submission_file_path)
        self.assertEqual(self.response.status_code, 201)

    def _publish_grouped_gps_form(self):
        xls_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures/grouped_gps.xls"
        )
        count = XForm.objects.count()
        response = self._publish_xls_file(xls_file_path)
        self.assertEqual(XForm.objects.count(), count + 1)
        self.xform = XForm.objects.all().reverse()[0]
        self.survey_name = u"grouped_gps"

    def _submit_grouped_gps_instance(self):
        xml_submission_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "fixtures/grouped_gps_01.xml"
        )
        self._make_submission(xml_submission_file_path)
        self.assertEqual(self.response.status_code, 201)

    def _xls_data_for_dataframe(self):
        xls_df_builder = XLSDataFrameBuilder(self.user.username, self.xform.id_string)
        cursor = xls_df_builder._query_mongo()
        return xls_df_builder._format_for_dataframe(cursor)

    def _csv_data_for_dataframe(self):
        csv_df_builder = CSVDataFrameBuilder(self.user.username, self.xform.id_string)
        cursor = csv_df_builder._query_mongo()
        return csv_df_builder._format_for_dataframe(cursor)

    def test_generated_sections(self):
        self._publish_single_level_repeat_form()
        self._submit_single_level_repeat_instance()
        xls_df_builder = XLSDataFrameBuilder(self.user.username, self.xform.id_string)
        expected_section_keys = [self.survey_name, u"kids_details"]
        section_keys = [s[u"name"] for s in xls_df_builder.sections]
        self.assertEqual(sorted(expected_section_keys), sorted(section_keys))

    def test_row_counts(self):
        """
        Test the number of rows in each sheet

        We expect a single row in the main new_repeats sheet and 2 rows in the kids details sheet one for each repeat
        """
        self._publish_single_level_repeat_form()
        self._submit_single_level_repeat_instance()
        data = self._xls_data_for_dataframe()
        self.assertEqual(len(data[self.survey_name]), 1)
        self.assertEqual(len(data[u"kids_details"]), 2)

    def test_xls_columns(self):
        """
        Test that our expected columns are in the data
        """
        self._publish_single_level_repeat_form()
        self._submit_single_level_repeat_instance()
        data = self._xls_data_for_dataframe()
        # columns in the default sheet
        expected_default_columns = [
            u"gps",
            u"_gps_latitude",
            u"_gps_longitude",
            u"_gps_altitude",
            u"_gps_precision",
            u"web_browsers/firefox",
            u"web_browsers/safari",
            u"web_browsers/ie",
            u"info/age",
            u"web_browsers/chrome",
            u"kids/has_kids",
            u"info/name"
        ] + XLSDataFrameBuilder.EXTRA_COLUMNS
        default_columns = [k for k in data[self.survey_name][0]]
        self.assertEqual(sorted(expected_default_columns), sorted(default_columns))

        # columns in the kids_details sheet
        expected_kids_details_columns = [u"kids/kids_details/kids_name", u"kids/kids_details/kids_age"] \
          + XLSDataFrameBuilder.EXTRA_COLUMNS
        kids_details_columns = [k for k in data[u"kids_details"][0]]
        self.assertEqual(sorted(expected_kids_details_columns), sorted(kids_details_columns))

    def test_xls_columns_for_gps_within_groups(self):
        """
        Test that a valid xpath is generated for extra gps fields that are NOT
        top level
        """
        self._publish_grouped_gps_form()
        self._submit_grouped_gps_instance()
        data = self._xls_data_for_dataframe()
        # columns in the default sheet
        expected_default_columns = [
            u"gps_group/gps",
            u"gps_group/_gps_latitude",
            u"gps_group/_gps_longitude",
            u"gps_group/_gps_altitude",
            u"gps_group/_gps_precision",
            u"web_browsers/firefox",
            u"web_browsers/safari",
            u"web_browsers/ie",
            u"web_browsers/chrome",
        ] + XLSDataFrameBuilder.EXTRA_COLUMNS
        default_columns = [k for k in data[self.survey_name][0]]
        self.assertEqual(sorted(expected_default_columns),
            sorted(default_columns))

    def test_csv_columns(self):
        self._publish_nested_repeats_form()
        self._submit_nested_repeats_instance()
        data = self._csv_data_for_dataframe()
        columns = data[0].keys()
        expected_columns = [
            u'kids/has_kids',
            u'kids/kids_details[1]/kids_name',
            u'kids/kids_details[1]/kids_age',
            u'kids/kids_details[1]/kids_immunization[1]/immunization_info',
            u'kids/kids_details[1]/kids_immunization[2]/immunization_info',
            u'kids/kids_details[1]/kids_immunization[3]/immunization_info',
            u'kids/kids_details[2]/kids_name',
            u'kids/kids_details[2]/kids_age',
            u'kids/kids_details[2]/kids_immunization[1]/immunization_info',
            u'kids/kids_details[2]/kids_immunization[2]/immunization_info',
            u'kids/nested_group/nested_name',
            u'kids/nested_group/nested_age',
            u'gps',
            u'_gps_latitude',
            u'_gps_longitude',
            u'_gps_altitude',
            u'_gps_precision',
            u'web_browsers/firefox',
            u'web_browsers/chrome',
            u'web_browsers/ie',
            u'web_browsers/safari',
        ]
        self.maxDiff = None
        self.assertEqual(sorted(expected_columns), sorted(columns))

    def test_csv_columns_for_gps_within_groups(self):
        self._publish_grouped_gps_form()
        self._submit_grouped_gps_instance()
        data = self._csv_data_for_dataframe()
        columns = data[0].keys()
        expected_columns = [
            u'gps_group/gps',
            u'gps_group/_gps_latitude',
            u'gps_group/_gps_longitude',
            u'gps_group/_gps_altitude',
            u'gps_group/_gps_precision',
            u'web_browsers/firefox',
            u'web_browsers/chrome',
            u'web_browsers/ie',
            u'web_browsers/safari',
        ]
        self.maxDiff = None
        self.assertEqual(sorted(expected_columns), sorted(columns))

    def test_format_mongo_data_for_csv_columns(self):
        self._publish_single_level_repeat_form()
        self._submit_single_level_repeat_instance()
        dd = self.xform.data_dictionary()
        columns = dd.get_keys()
        data = self._csv_data_for_dataframe()
        expected_data_0 = {u'gps': u'-1.2627557 36.7926442 0.0 30.0', u'kids/has_kids': u'1', u'_attachments': [],
                          u'info/age': u'80', u'_xform_id_string': u'new_repeat', u'_status': u'submitted_via_web',
                          u'kids/kids_details/kids_name': u'Abel', u'kids/kids_details/kids_age': u'50',
                          u'kids/kids_details[2]/kids_name': u'Cain', u'kids/kids_details[2]/kids_age': u'76',
                          u'web_browsers/chrome': u'TRUE', u'web_browsers/ie': u'TRUE',
                          u'web_browsers/safari': u'FALSE', u'web_browsers/firefox': u'FALSE', u'info/name': u'Adam'}
        #self.assertEqual(sorted(expected_data_0.keys()), sorted(data[0].keys()))

    def test_split_select_multiples(self):
        self._publish_nested_repeats_form()
        dd = self.xform.data_dictionary()
        self._submit_nested_repeats_instance()
        csv_df_builder = CSVDataFrameBuilder(self.user.username, self.xform.id_string)
        cursor = csv_df_builder._query_mongo()
        record = cursor[0]
        select_multiples = CSVDataFrameBuilder._collect_select_multiples(dd)
        result = CSVDataFrameBuilder._split_select_multiples(record,
            select_multiples)
        expected_result = {
            u'web_browsers/ie': True,
            u'web_browsers/safari': True,
            u'web_browsers/firefox': False,
            u'web_browsers/chrome': False
        }
        # build a new dictionary only composed of the keys we want to use in the comparison
        result = dict([(key, result[key]) for key in result.keys() if key in expected_result.keys()])
        self.assertEqual(expected_result, result)

    def test_split_select_multiples_within_repeats(self):
        self.maxDiff = None
        record = {
            'name': 'Tom',
            'age': 23,
            'browser_use': [
                {
                    'browser_use/year': '2010',
                    'browser_use/browsers': 'firefox safari'
                },
                {
                    'browser_use/year': '2011',
                    'browser_use/browsers': 'firefox chrome'
                }
            ]
        }
        expected_result = {
            'name': 'Tom',
            'age': 23,
            'browser_use': [
                {
                    'browser_use/year': '2010',
                    'browser_use/browsers/firefox': True,
                    'browser_use/browsers/safari': True,
                    'browser_use/browsers/ie': False,
                    'browser_use/browsers/chrome': False
                },
                {
                    'browser_use/year': '2011',
                    'browser_use/browsers/firefox': True,
                    'browser_use/browsers/safari': False,
                    'browser_use/browsers/ie': False,
                    'browser_use/browsers/chrome': True
                }
            ]
        }
        select_multiples = {
            'browser_use/browsers':
                [
                    'browser_use/browsers/firefox',
                    'browser_use/browsers/safari',
                    'browser_use/browsers/ie',
                    'browser_use/browsers/chrome'
                ]
            }
        result = CSVDataFrameBuilder._split_select_multiples(record,
            select_multiples)
        self.assertEqual(expected_result, result)

    def test_split_gps_fields(self):
        record = {
            'gps': '5 6 7 8'
        }
        gps_fields = ['gps']
        expected_result = {
            'gps': '5 6 7 8',
            '_gps_latitude': '5',
            '_gps_longitude': '6',
            '_gps_altitude': '7',
            '_gps_precision': '8',
        }
        AbstractDataFrameBuilder._split_gps_fields(record, gps_fields)
        self.assertEqual(expected_result, record)

    def test_split_gps_fields_within_repeats(self):
        record = {
            'a_repeat': [
                {
                    'gps': '1 2 3 4'
                },
                {
                    'gps': '5 6 7 8'
                }
            ]
        }
        gps_fields = ['gps']
        expected_result = {
            'a_repeat': [
                {
                    'gps': '1 2 3 4',
                    '_gps_latitude': '1',
                    '_gps_longitude': '2',
                    '_gps_altitude': '3',
                    '_gps_precision': '4',
                },
                {
                    'gps': '5 6 7 8',
                    '_gps_latitude': '5',
                    '_gps_longitude': '6',
                    '_gps_altitude': '7',
                    '_gps_precision': '8',
                }
            ]
        }
        AbstractDataFrameBuilder._split_gps_fields(record, gps_fields)
        self.assertEqual(expected_result, record)

    def test_valid_sheet_name(self):
        sheet_names = ["sheet_1", "sheet_2"]
        desired_sheet_name = "sheet_3"
        expected_sheet_name = "sheet_3"
        generated_sheet_name = get_valid_sheet_name(desired_sheet_name, sheet_names)
        self.assertEqual(generated_sheet_name, expected_sheet_name)

    def test_invalid_sheet_name(self):
        sheet_names = ["sheet_1", "sheet_2"]
        desired_sheet_name = "sheet_3_with_more_than_max_expected_length"
        expected_sheet_name = "sheet_3_with_more_than_max_exp"
        generated_sheet_name = get_valid_sheet_name(desired_sheet_name, sheet_names)
        self.assertEqual(generated_sheet_name, expected_sheet_name)

    def test_duplicate_sheet_name(self):
        sheet_names = ["sheet_2_with_duplicate_sheet_n", "sheet_2_with_duplicate_sheet_1"]
        duplicate_sheet_name = "sheet_2_with_duplicate_sheet_n"
        expected_sheet_name  = "sheet_2_with_duplicate_sheet_2"
        generated_sheet_name = get_valid_sheet_name(duplicate_sheet_name, sheet_names)
        self.assertEqual(generated_sheet_name, expected_sheet_name)
