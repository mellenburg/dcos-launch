"""DC/OS Launch

Usage:
  dcos-launch create [-L LEVEL -c PATH -i PATH]
  dcos-launch wait [-L LEVEL -i PATH]
  dcos-launch describe [-L LEVEL -i PATH]
  dcos-launch pytest [-L LEVEL -i PATH -e LIST] [--] [<pytest_extras>]...
  dcos-launch delete [-L LEVEL -i PATH]

Commands:
  create    Reads the file given by --config-path, creates the cluster
              described therein and finally dumps a JSON file to the path
              given in --info-path which can then be used with the wait,
              describe, pytest, and delete calls.
  wait      Block until the cluster is up and running.
  describe  Return additional information about the composition of the cluster.
  pytest    Runs integration test suite on cluster. Can optionally supply
              options and arguments to pytest
  delete    Destroying the provided cluster deployment.

Options:
  -c PATH --config-path=PATH
            Path for config to create cluster from [default: config.yaml].
  -i PATH --info-path=PATH
            JSON file output by create and consumed by wait, describe,
            and delete [default: cluster_info.json].
  -e LIST --env=LIST
            Specifies a comma-delimited list of environment variables to be
            passed from the local environment into the test environment.
  -L LEVEL --log-level=LEVEL
            One of: critical, error, warning, info, debug, and trace
            [default: info].
"""
import json
import os
import sys

from docopt import docopt

import dcos_launch
import dcos_launch.config
import dcos_launch.util
from dcos_test_utils import logging

json_prettyprint_args = {
    "sort_keys": True,
    "indent": 2,
    "separators": (',', ':')
}


def write_json(filename, data):
    with open(filename, "w+") as f:
        return json.dump(data, f, **json_prettyprint_args)


def json_prettyprint(data):
    return json.dumps(data, **json_prettyprint_args)


def load_json(filename):
    try:
        with open(filename) as f:
            return json.load(f)
    except ValueError as ex:
        raise ValueError("Invalid JSON in {0}: {1}".format(filename, ex)) from ex


def do_main(args):
    logging.setup_logging(args['--log-level'].upper())

    config_path = args['--config-path']
    if args['create']:
        config = dcos_launch.config.get_validated_config(config_path)
        info_path = args['--info-path']
        if os.path.exists(info_path):
            raise dcos_launch.util.LauncherError(
                'InputConflict',  '{} already exists! Delete this or specify a '
                'different cluster info path with the -i option'.format(info_path))
        write_json(info_path, dcos_launch.get_launcher(config).create())
        return 0

    try:
        info = load_json(args['--info-path'])
    except FileNotFoundError as ex:
        raise dcos_launch.util.LauncherError('MissingInfoJSON', None) from ex

    launcher = dcos_launch.get_launcher(info)

    if args['wait']:
        launcher.wait()
        print('Cluster is ready!')
        return 0

    if args['describe']:
        print(json_prettyprint(launcher.describe()))
        return 0

    if args['pytest']:
        var_list = list()
        if args['--env'] is not None:
            if '=' in args['--env']:
                # User is attempting to do an assigment with the option
                raise dcos_launch.util.LauncherError(
                    'OptionError', "The '--env' option can only pass through environment variables "
                    "from the current environment. Set variables according to the shell being used.")
            var_list = args['--env'].split(',')
            missing = [v for v in var_list if v not in os.environ]
            if len(missing) > 0:
                raise dcos_launch.util.LauncherError(
                    'MissingInput', 'Environment variable arguments have been indicated '
                    'but not set: {}'.format(repr(missing)))
        env_dict = {e: os.environ[e] for e in var_list}
        return launcher.test(args['<pytest_extras>'], env_dict)

    if args['delete']:
        launcher.delete()
        return 0


def main(argv=None):
    args = docopt(__doc__, argv=argv, version='DC/OS Launch v.0.1')

    try:
        return do_main(args)
    except dcos_launch.util.LauncherError as ex:
        print('DC/OS Launch encountered an error!')
        print(repr(ex))
        return 1


if __name__ == '__main__':
    sys.exit(main())
