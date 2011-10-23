import os.path
import simplejson
import sys

import argparse

from dogapi.v1 import DashService

from dogshell.common import report_errors, report_warnings, CommandLineClient

class DashClient(CommandLineClient):

    def __init__(self, config):
        self.config = config

    def setup_parser(self, subparsers):
        parser = subparsers.add_parser('dashboard', help='Create, edit, and delete dashboards.')
        verb_parsers = parser.add_subparsers(title='Verbs')

        post_parser = verb_parsers.add_parser('post', help='Create dashboards.')
        post_parser.add_argument('title', help='title for the new dashboard')
        post_parser.add_argument('description', help='short description of the dashboard')
        post_parser.add_argument('graphs', help='graph definitions as a JSON string. if unset, reads from stdin.', nargs="?")
        post_parser.set_defaults(func=self._post)

        update_parser = verb_parsers.add_parser('update', help='Update existing dashboards.')
        update_parser.add_argument('dashboard_id', help='dashboard to replace with the new definition')
        update_parser.add_argument('title', help='new title for the dashboard')
        update_parser.add_argument('description', help='short description of the dashboard')
        update_parser.add_argument('graphs', help='graph definitions as a JSON string. if unset, reads from stdin.', nargs="?")
        update_parser.set_defaults(func=self._update)

        show_parser = verb_parsers.add_parser('show', help='Show a dashboard definition.')
        show_parser.add_argument('dashboard_id', help='dashboard to show')
        show_parser.set_defaults(func=self._show)

        show_all_parser = verb_parsers.add_parser('show_all', help='Show a list of all dashboards.')
        show_all_parser.set_defaults(func=self._show_all)

        pull_parser = verb_parsers.add_parser('pull', help='Pull a dashboard on the server into a local file')
        pull_parser.add_argument('dashboard_id', help='ID of dashboard to pull')
        pull_parser.add_argument('filename', help='file to pull dashboard into') # , type=argparse.FileType('wb'))
        pull_parser.set_defaults(func=self._pull)

        pull_all_parser = verb_parsers.add_parser('pull_all', help='Pull all dashboards into files in a directory')
        pull_all_parser.add_argument('pull_dir', help='directory to pull dashboards into')
        pull_all_parser.set_defaults(func=self._pull_all)

        push_parser = verb_parsers.add_parser('push', help='Push updates to dashboards from local files to the server')
        push_parser.add_argument('file', help='dashboard files to push to the server', nargs='+', type=argparse.FileType('r'))
        push_parser.set_defaults(func=self._push)

        new_file_parser = verb_parsers.add_parser('new_file', help='Create a new dashboard and put its contents in a file')
        new_file_parser.add_argument('filename', help='name of file to create with empty dashboard')
        new_file_parser.set_defaults(func=self._new_file)

        delete_parser = verb_parsers.add_parser('delete', help='Delete dashboards.')
        delete_parser.add_argument('dashboard_id', help='dashboard to delete')
        delete_parser.set_defaults(func=self._delete)


    def _write_dash_to_file(self, dash_id, filename):
        svc = DashService(self.config['apikey'], self.config['appkey'])
        with open(filename, "wb") as f:
            res = svc.get(dash_id)
            dash_obj = res["dash"]
            report_warnings(res)
            report_errors(res)

            # Deleting these because they don't match the REST API and could confuse
            del dash_obj["resource"]
            del dash_obj["url"]
            simplejson.dump(dash_obj, f, indent=2)

    def _pull(self, args):
        self._write_dash_to_file(args.dashboard_id, args.filename)

    def _pull_all(self, args):
        
        def _title_to_filename(title):
            # Get a lowercased version with most punctuation stripped out...
            no_punct = filter(lambda c: c.isalnum() or c in [" ", "_", "-"],
                              title.lower())
            # Now replace all -'s, _'s and spaces with "_", and strip trailing _
            return no_punct.replace(" ", "_").replace("-", "_").strip("_")

        format = args.format
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.get_all()
        report_warnings(res)
        report_errors(res)
        
        if not os.path.exists(args.pull_dir):
            os.mkdir(args.pull_dir, 0755)
        
        used_filenames = set()
        for dash_summary in res['dashes']:
            filename = _title_to_filename(dash_summary['title'])
            if filename in used_filenames:
                filename = filename + "-" + dash_summary['id']
            used_filenames.add(filename)

            self._write_dash_to_file(dash_summary['id'], 
                                     os.path.join(args.pull_dir, filename + ".json"))
        
        if format == 'pretty':
            print("Downloaded {0} dashboards to {1}"
                  .format(len(used_filenames), os.path.realpath(args.pull_dir)))

    def _new_file(self, args):
        format = args.format
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.create(args.filename, 
                         "Description for {0}".format(args.filename), [])
        report_warnings(res)
        report_errors(res)
        
        self._write_dash_to_file(res['dash']['id'], args.filename)

        # Er... look into what these actually do
        if format == 'pretty':
            print res
        elif format == 'raw':
            print res
        else:
            print res

    def _push(self, args):
        svc = DashService(self.config['apikey'], self.config['appkey'])
        for f in args.file:
            dash_obj = simplejson.load(f)
            res = svc.update(dash_obj["id"], dash_obj["title"], 
                             dash_obj["description"], dash_obj["graphs"])
            report_warnings(res)
            report_errors(res)
        
    def _post(self, args):
        format = args.format
        if args.graphs is None:
            graphs = sys.stdin.read()
        try:
            graphs = simplejson.loads(graphs)
        except:
            raise Exception('bad json parameter')
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.create(args.title, args.description, graphs)
        report_warnings(res)
        report_errors(res)
        if format == 'pretty':
            print res
        elif format == 'raw':
            print res
        else:
            print res

    def _update(self, args):
        format = args.format
        if args.graphs is None:
            graphs = sys.stdin.read()
        try:
            graphs = simplejson.loads(graphs)
        except:
            raise Exception('bad json parameter')
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.update(args.dashboard_id, args.title, args.description, graphs)
        report_warnings(res)
        report_errors(res)
        if format == 'pretty':
            print res
        elif format == 'raw':
            print res
        else:
            print res

    def _show(self, args):
        format = args.format
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.get(args.dashboard_id)
        report_warnings(res)
        report_errors(res)
        if format == 'pretty':
            print simplejson.dumps(res, sort_keys=True, indent=2)
        elif format == 'raw':
            print res
        else:
            print res

    def _show_all(self, args):
        format = args.format
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.get_all()
        report_warnings(res)
        report_errors(res)
        if format == 'pretty':
            print simplejson.dumps(res, sort_keys=True, indent=2)
        elif format == 'raw':
            print res
        else:
            print res

    def _delete(self, args):
        format = args.format
        svc = DashService(self.config['apikey'], self.config['appkey'])
        res = svc.delete(args.dashboard_id)
        report_warnings(res)
        report_errors(res)
        if format == 'pretty':
            print res
        elif format == 'raw':
            print res
        else:
            print res
