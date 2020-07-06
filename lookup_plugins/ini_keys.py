import os
from io import StringIO
from ansible.errors import AnsibleError, AnsibleParserError
from ansible.plugins.lookup import LookupBase
from ansible.module_utils._text import to_text
from ansible.module_utils.six.moves import configparser

class LookupModule(LookupBase):
    def run(self, terms, variables=None, **kwargs):
        ret = []
        for term in terms:
            params = {
                'section': 'global',
                'file': 'ansible.ini',
                'encoding': 'utf-8',
            }
            for arg in term.split(' '):
                k, v = arg.split('=', 1)
                params[k] = v

            # Load file data.
            path = self.find_file_in_search_path(variables, 'files', params['file'])
            contents, show_data = self._loader._get_file_contents(path)
            contents = to_text(contents, errors='surrogate_or_strict',
                               encoding=params['encoding'])
            config = StringIO()
            config.write(contents)
            config.seek(0, os.SEEK_SET)

            cp = configparser.ConfigParser()
            cp.read_file(config)
            ret += cp.options(params['section'])
        return ret


