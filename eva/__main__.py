import traceback
import argparse
import ConfigParser
import logging
import logging.config

import productstatus

import eva.eventloop
import eva.adapter
import eva.executor


def import_module_class(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


def add_commandline_arguments(argument_parser):
    argument_parser.add_argument('--log-config', action='store', required=True,
                                 help='Path to logging configuration file')

    # Configuration of Productstatus client.
    argument_parser.add_argument('--productstatus-url', action='store', required=True,
                                 help='URL to Productstatus service')
    argument_parser.add_argument('--productstatus-username', action='store', required=False,
                                 help='Productstatus username for authentication')
    argument_parser.add_argument('--productstatus-api-key', action='store', required=False,
                                 help='Productstatus API key matching the username')
    argument_parser.add_argument('--productstatus-event-socket', action='store', required=True,
                                 help='Socket for receiving Productstatus events')
    argument_parser.add_argument('--productstatus-no-verify-ssl', action='store_true', default=False,
                                 help='Set this option to skip Productstatus SSL certificate verification')

    # Configuration options for EVA about how to run and what jobs to run.
    argument_parser.add_argument('--adapter', action='append', required=False,
                                 help='Python class name of adapters that should be run; repeat argument for each adapter')
    argument_parser.add_argument('--executor', action='store', required=False, default='eva.executor.NullExecutor',
                                 help='Python class name of executor that should be used')


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()

    add_commandline_arguments(argument_parser)

    args = argument_parser.parse_args()
    logging.config.fileConfig(args.log_config)

    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(args.log_config)

    productstatus_api = productstatus.api.Api(args.productstatus_url,
                                              username=args.productstatus_username,
                                              api_key=args.productstatus_api_key,
                                              verify_ssl=not args.productstatus_no_verify_ssl)

    loop_interval = 10000
    event_listener = productstatus.event.Listener(args.productstatus_event_socket,
                                                  timeout=loop_interval)

    adapters = []
    for adapter_name in args.adapter:
        adapter_class = import_module_class(adapter_name)
        adapter_instance = adapter_class(productstatus_api)
        logging.info('Adding adapter: %s' % adapter_instance.__class__)
        adapters.append(adapter_instance)

    executor = import_module_class(args.executor)()
    logging.info('Using executor: %s' % executor.__class__)

    try:
        evaloop = eva.eventloop.Eventloop(productstatus_api, event_listener, adapters, executor)
        evaloop()
    except KeyboardInterrupt:
        pass
    except Exception, e:
        logging.critical("Fatal error: %s" % e)
        exception = traceback.format_exc().split("\n")
        logging.debug("***********************************************************")
        logging.debug("Uncaught exception during program execution. THIS IS A BUG!")
        logging.debug("***********************************************************")
        for line in exception:
            logging.debug(line)
        exit_code = 255
