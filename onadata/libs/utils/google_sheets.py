"""
This module contains classes responsible for communicating with
Google Data API and common spreadsheets models.
"""

import gdata.gauth
import gspread 
import json
    
from django.conf import settings
from onadata.libs.utils.google import get_refreshed_token
from onadata.libs.utils.export_builder import ExportBuilder
from onadata.libs.utils.common_tags import INDEX, PARENT_INDEX, PARENT_TABLE_NAME

    
class SheetsClient(gspread.client.Client):
    """An instance of this class communicates with Google Data API."""
    
    def new(self, title):
        create_url = 'https://www.googleapis.com/drive/v2/files'
        headers = {'Content-Type': 'application/json'}
        data = {
            'title': title, 
            'mimeType': 'application/vnd.google-apps.spreadsheet'
        }
        r = self.session.request(
            'POST', create_url, headers=headers, data=json.dumps(data))
        resp = json.loads(r.read().decode('utf-8'))
        sheet_id = resp['id']
        return self.open_by_key(sheet_id)


class SheetsExportBuilder(ExportBuilder):
    client = None
    spreadsheet = None
    # Worksheets generated by this class.
    worksheets = {}
    # Map of section_names to generated_names
    worksheet_titles = {}
    
    def login_with_auth_token(self, token):
        if token.refresh_token is None or token.access_token is None:
            # Failed :-(
            return
        
        # Refresh OAuth token if necessary.
        oauth2_token = gdata.gauth.OAuth2Token(
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scope=' '.join(
                ['https://docs.google.com/feeds/',
                 'https://spreadsheets.google.com/feeds/',
                 'https://www.googleapis.com/auth/drive.file']),
            user_agent='formhub')
        oauth2_token.refresh_token = token.refresh_token
        refreshed_token = get_refreshed_token(oauth2_token)
    
        # Create Google Sheet.
        self.client = SheetsClient(auth=refreshed_token)
        self.client.login()
    
    def export(self, path, data, *args):
        assert self.client
        
        # Create a new sheet
        print 'SheetsExportBuilder: creating new spreadsheet'
        self.spreadsheet = self.client.new(title=path)
        
        # Add worksheets for export. 
        print 'SheetsExportBuilder: adding worksheet'
        self._create_worksheets()
        
        # Write the headers
        print 'SheetsExportBuilder: inserting headers'
        self._insert_headers()

        # Write the data
        print 'SheetsExportBuilder: inserting data'
        self._insert_data(data)
        
        print 'SheetsExportBuilder: done'
    
    def _insert_data(self, data):
        """Writes data rows for each section."""
        index = 1
        indices = {}
        survey_name = self.survey.name
        for d in data:
            joined_export = ExportBuilder.dict_to_joined_export(
                d, index, indices, survey_name)
            output = ExportBuilder.decode_mongo_encoded_section_names(
                joined_export)
            print 'output'
            print output
            # attach meta fields (index, parent_index, parent_table)
            # output has keys for every section
            if survey_name not in output:
                output[survey_name] = {}
            output[survey_name][INDEX] = index
            output[survey_name][PARENT_INDEX] = -1
            for section in self.sections:
                # get data for this section and write to xls
                section_name = section['name']
                fields = [
                    element['xpath'] for element in
                    section['elements']] + self.EXTRA_FIELDS

                ws = self.worksheets[section_name]
                # section might not exist within the output, e.g. data was
                # not provided for said repeat - write test to check this
                row = output.get(section_name, None)
                print 'row'
                print row
                if type(row) == dict:
                    SheetsExportBuilder.write_row(
                        self.pre_process_row(row, section),
                        ws, fields, self.worksheet_titles)
                elif type(row) == list:
                    for child_row in row:
                        SheetsExportBuilder.write_row(
                            self.pre_process_row(child_row, section),
                            ws, fields, self.worksheet_titles)
            index += 1
            
    def _insert_headers(self):
        """Writes headers for each section."""
        for section in self.sections:
            section_name = section['name']
            headers = [
                element['title'] for element in
                section['elements']] + self.EXTRA_FIELDS
            # get the worksheet
            ws = self.worksheets[section_name]
            ws.insert_row(values=headers, index=1)
            
    def _create_worksheets(self):
        """Creates one worksheet per section."""
        for section in self.sections:
            section_name = section['name']
            work_sheet_title = self.get_valid_sheet_name(
                "_".join(section_name.split("/")), 
                self.worksheet_titles.values())
            self.worksheet_titles[section_name] = work_sheet_title
            num_cols = len(section['elements']) + len(self.EXTRA_FIELDS)
            print 'adding ws %s' % work_sheet_title
            self.worksheets[section_name] = self.spreadsheet.add_worksheet(
                title=work_sheet_title, rows=1, cols=num_cols)
        # TODO: we need to either re-use or delete the default worksheet
        # ws = ss.get_worksheet(0)
        # ss.del_worksheet(ws)

    @classmethod    
    def write_row(cls, data, worksheet, fields, worksheet_titles):
        # update parent_table with the generated sheet's title
        data[PARENT_TABLE_NAME] = worksheet_titles.get(
            data.get(PARENT_TABLE_NAME))
        worksheet.append_row([data.get(f) for f in fields])
    